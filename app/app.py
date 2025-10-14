from flask import Flask, render_template, request, jsonify
import pandas as pd
import numpy as np
import os
from dotenv import load_dotenv
import psycopg2 
from sentence_transformers import SentenceTransformer
from pathlib import Path

# Load environment variables from .env file
dotenv_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv()
model = SentenceTransformer('all-MiniLM-L6-v2')

def connect():
    conn = psycopg2.connect(
        host=os.getenv("POSTGRES_HOST"),
        dbname=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        port=os.getenv("POSTGRES_PORT")
    )
    cursor = conn.cursor()

    return conn, cursor



app = Flask(__name__)

@app.route('/')
def home():
    return render_template("3d.html")

@app.route('/api/verses', methods=['GET'])
def get_initial_verses():
    conn, cursor = connect()

    try:
        cursor.execute("""
            SELECT id, citation, book_number, text
            FROM verses_table
        """)

        verses_rows = cursor.fetchall()

        cursor.execute("""
            SELECT id, embedding
            FROM embeddings_3d_table
        """)

        rows = cursor.fetchall()
        embeddings_3d = [np.fromstring(r[1].strip("[]"), sep=',', dtype=np.float32) for r in rows]
        id = [int(r[0]) for r in rows]

        verses = []
        for i, verse in enumerate(verses_rows):
            verses.append({
                "id": int(verse[0]),
                "citation": verse[1],
                "book": int(verse[2]),
                "text": verse[3],
                "coordinates": {
                    "x": float(embeddings_3d[i][0]),
                    "y": float(embeddings_3d[i][1]),
                    "z": float(embeddings_3d[i][2])
                }
            })

        print(len(verses))
        return jsonify({"verses": verses}), 200

    except Exception as e:
        print(f"Error fetching initial data: {e}")
        return jsonify({"error": "Error fetching initial data"}), 500
    
    finally:
        cursor.close()
        conn.close()

@app.route('/find_similar', methods=['POST'])
def find_similar():
    id = request.json.get('id')
    id = int(id)

    print(id)
    
    conn, cursor = connect()

    try:
        # finding similar verses
        cursor.execute("""
            SELECT similar_id, rank, similarity
            FROM each_verse_similarity_table
            WHERE verse_id = %s 
            ORDER BY rank
            LIMIT 30;
        """, (id,))

        similar_ids = []
        similarities = []

        for row in cursor.fetchall():
            similar_ids.append(int(row[0]))
            similarities.append(float(row[2]))

        verses_results = []

        for i, similar_id in enumerate(similar_ids):

            verses_results.append({
                "id": similar_id,
                "similarity": similarities[i],
            })
        
        return jsonify({"results": verses_results}), 200

    except Exception as e:
        print(f"Error fetching similar verses: {e}")
        return jsonify({"error": "Error fetching similar verses"}), 500

    finally:
        cursor.close()
        conn.close()

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

        similarities = model.similarity([embedding], embeddings)[0].detach().cpu().numpy()
        
        print("embedding:", type(embedding), np.shape(embedding))
        print("embeddings:", type(embeddings), np.shape(embeddings))
        print("similarities:", type(similarities), np.shape(similarities))
        print("ids:", type(ids), np.shape(ids))

        top_indices = np.argsort(similarities)[-30:][::-1]
        top_ids = ids[top_indices]
        top_similarities = similarities[top_indices]
        
        verse_results = []
        for i in range(len(top_ids)):
            verse_results.append({
                "id": int(top_ids[i]),
                "similarity": float(top_similarities[i])
            })

        return jsonify({"results": verse_results}), 200

    except Exception as e:
        print(f"Error fetching similar verses: {e}")
        return jsonify({"error": "Error fetching similar verses"}), 500

    finally:
        cursor.close()
        conn.close()
    


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)
    