from flask import Flask, render_template, request, jsonify
import pandas as pd
import numpy as np
import os
from dotenv import load_dotenv
import psycopg2
from psycopg2 import pool
from sentence_transformers import SentenceTransformer
from pathlib import Path

# For Google Cloud deployment
PORT = 8080 

# Load environment variables from .env file
dotenv_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv()
model = SentenceTransformer('all-MiniLM-L6-v2')

# Create a connection pool for better performance
# Reuses connections instead of creating new ones for each request
connection_pool = pool.SimpleConnectionPool(
    1,  # minimum connections
    10,  # maximum connections
    url=os.getenv("SUPABASE_URL")
)

def connect():
    conn = connection_pool.getconn()
    cursor = conn.cursor()
    return conn, cursor

def release_connection(conn):
    connection_pool.putconn(conn)



app = Flask(__name__)

@app.route('/')
def home():
    return render_template("3d.html")

@app.route('/api/verses', methods=['GET'])
def get_initial_verses():
    conn, cursor = connect()

    try:
        cursor.execute("""
            SELECT id, embedding
            FROM embeddings_3d_table
        """)

        rows = cursor.fetchall()
        embeddings_3d = [np.fromstring(r[1].strip("[]"), sep=',', dtype=np.float32) for r in rows]
        ids = [int(r[0]) for r in rows]

        verses = []
        for i, verse_id in enumerate(ids):
            verses.append({
                "id": verse_id,
                "coordinates": {
                    "x": float(embeddings_3d[i][0]),
                    "y": float(embeddings_3d[i][1]),
                    "z": float(embeddings_3d[i][2])
                }
            })

        print(f"Loaded {len(verses)} verses with id and coordinates only")
        return jsonify({"verses": verses}), 200

    except Exception as e:
        print(f"Error fetching initial data: {e}")
        return jsonify({"error": "Error fetching initial data"}), 500

    finally:
        cursor.close()
        release_connection(conn)

@app.route('/api/verse/<int:verse_id>', methods=['GET'])
def get_verse(verse_id):
    conn, cursor = connect()

    try:
        cursor.execute("""
            SELECT id, citation, text
            FROM verses_table
            WHERE id = %s
        """, (verse_id,))

        verse_row = cursor.fetchone()

        if not verse_row:
            return jsonify({"error": "Verse not found"}), 404

        verse = {
            "id": int(verse_row[0]),
            "citation": verse_row[1],
            "text": verse_row[2]
        }

        return jsonify(verse), 200

    except Exception as e:
        print(f"Error fetching verse {verse_id}: {e}")
        return jsonify({"error": "Error fetching verse"}), 500

    finally:
        cursor.close()
        release_connection(conn)

@app.route('/find_similar', methods=['POST'])
def find_similar():
    id = request.json.get('id')
    id = int(id)

    print(f"Finding similar verses for ID: {id}")

    conn, cursor = connect()

    try:
        # Get original verse details
        cursor.execute("""
            SELECT id, citation, text
            FROM verses_table
            WHERE id = %s
        """, (id,))

        original_row = cursor.fetchone()
        if not original_row:
            return jsonify({"error": "Original verse not found"}), 404

        original_verse = {
            "id": int(original_row[0]),
            "citation": original_row[1],
            "text": original_row[2]
        }

        # Find similar verses with their details
        cursor.execute("""
            SELECT
                s.similar_id,
                s.similarity,
                v.citation,
                v.text
            FROM each_verse_similarity_table s
            JOIN verses_table v ON s.similar_id = v.id
            WHERE s.verse_id = %s
            ORDER BY s.rank
            LIMIT 30;
        """, (id,))

        verses_results = []
        for row in cursor.fetchall():
            verses_results.append({
                "id": int(row[0]),
                "similarity": float(row[1]),
                "citation": row[2],
                "text": row[3]
            })

        return jsonify({
            "original_verse": original_verse,
            "results": verses_results
        }), 200

    except Exception as e:
        print(f"Error fetching similar verses: {e}")
        return jsonify({"error": "Error fetching similar verses"}), 500

    finally:
        cursor.close()
        release_connection(conn)

@app.route('/find_query', methods=['POST'])
def find_query():
    query = str(request.json.get('query'))
    embedding = model.encode([query])[0]

    conn, cursor = connect()

    try:
        cursor.execute("""
            SELECT id, embedding FROM embeddings_table
        """)

        rows = cursor.fetchall()

        embeddings = np.array([
            np.fromstring(r[1].strip("[]"), sep=',', dtype=np.float32)
            for r in rows
        ], dtype=np.float32)

        ids = np.array([int(r[0]) for r in rows], dtype=np.int32)

        # Reshape embedding to 2D array for model.similarity (expects batch dimension)
        # This avoids the warning about converting list of numpy arrays to tensor
        embedding_batch = embedding.reshape(1, -1)
        similarities = model.similarity(embedding_batch, embeddings)[0].detach().cpu().numpy()

        top_indices = np.argsort(similarities)[-30:][::-1]
        top_ids = ids[top_indices]
        top_similarities = similarities[top_indices]

        # Fetch verse details for top results
        verse_results = []
        for i in range(len(top_ids)):
            verse_id = int(top_ids[i])
            cursor.execute("""
                SELECT citation, text
                FROM verses_table
                WHERE id = %s
            """, (verse_id,))

            verse_row = cursor.fetchone()
            if verse_row:
                verse_results.append({
                    "id": verse_id,
                    "similarity": float(top_similarities[i]),
                    "citation": verse_row[0],
                    "text": verse_row[1]
                })

        return jsonify({"results": verse_results}), 200

    except Exception as e:
        print(f"Error fetching similar verses: {e}")
        return jsonify({"error": "Error fetching similar verses"}), 500

    finally:
        cursor.close()
        release_connection(conn)
    


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=PORT, debug=True)
    