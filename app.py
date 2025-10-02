from flask import Flask, render_template, request, jsonify
import pandas as pd
import numpy as np
import os
from dotenv import load_dotenv
import psycopg2 
import umap
from sentence_transformers import SentenceTransformer

# Load environment variables from .env file
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

def calculate_umap(embeddings):

    reducer = umap.UMAP(
        n_neighbors=10,
        n_components=3,
        metric='cosine',
        random_state=42
    )

    embeddings_3d = reducer.fit_transform(embeddings)

    return embeddings_3d



app = Flask(__name__)

@app.route('/')
def home():
    return render_template("index.html")

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

        similar_ids.append(id)
        similarities.append(1.0)
        for row in cursor.fetchall():
            similar_ids.append(int(row[0]))
            similarities.append(float(row[2]))

        citations = []
        texts = []

        for similar_id in similar_ids:

            cursor.execute("""
                SELECT citation, text
                FROM verses_table
                WHERE id = %s;
            """, (similar_id,))

            row = cursor.fetchone()
            citations.append(row[0])
            texts.append(row[1])

        embeddings = []
        for similar_id in similar_ids:

            cursor.execute("""
                SELECT embedding
                FROM embeddings_table
                WHERE id = %s;
            """, (similar_id,))

            # the pogresql is returning our embedding as string
            # so we convert it to array again
            embedding = cursor.fetchone()[0]
            embedding = embedding.strip("[]")
            embedding = np.fromstring(embedding, sep=', ', dtype=np.float32)

            embeddings.append(embedding)

        embeddings_3d = calculate_umap(embeddings)

        print(embeddings_3d)

        verses_results = []

        for i, similar_id in enumerate(similar_ids):

            verses_results.append({
                "id": similar_id,
                "citation": citations[i],
                "text": texts[i],
                "similarity": similarities[i],
                "coordinates": {
                    "x": float(embeddings_3d[i][0]),
                    "y": float(embeddings_3d[i][1]),
                    "z": float(embeddings_3d[i][2])
                }
            })
        
        return jsonify({"results": verses_results}), 200

    except Exception as e:
        print(f"Error fetching similar verses: {e}")
        return jsonify({"error": "Error fetching similar verses"}), 500

    finally:
        cursor.close()
        conn.close()
    
    return

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
        embeddings = [np.fromstring(r[1].strip("[]"), sep=',', dtype=np.float32) for r in rows]
        ids = [int(r[0]) for r in rows]

        similarirties = model.similarity([embedding], embeddings)[0]
        top_indices = np.argsort(similarirties)[-20:][::-1]
        top_ids = ids[top_indices]
        top_similarities = similarirties[top_indices]

        citations = []
        texts = []
        for id in top_ids:
            cursor.execute("""
                SELECT citation, text
                FROM verses_table
                WHERE id = %s;
            """, (id,))

            row = cursor.fetchone()
            citations.append(row[0])
            texts.append(row[1])
        
        verse_results = []
        for i, id in enumerate(top_ids):
            verse_results.append({
                "id": int(id),
                "citation": citations[i],
                "text": texts[i],
                "similarity": top_similarities[i]
            })

        return jsonify({"results": verse_results}), 200

    except Exception as e:
        print(f"Error fetching similar verses: {e}")
        return jsonify({"error": "Error fetching similar verses"}), 500

    finally:
        cursor.close()
        conn.close()
    


if __name__ == '__main__':
    find_query()
    app.run(host="0.0.0.0", port=5000, debug=True)
    