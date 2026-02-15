from flask import Flask, render_template, request, jsonify
import numpy as np
import os
import threading
from dotenv import load_dotenv
from psycopg2 import pool
from huggingface_hub import InferenceClient

load_dotenv()

# For Google Cloud deployment
PORT = int(os.environ.get("PORT", 5000))

# using hugging face api to reduce memory usage on deployment
HF_TOKEN = os.environ.get('HF_TOKEN')
client = InferenceClient(token=HF_TOKEN)

def get_embedding(text):
    embedding = client.feature_extraction(
        text,
        model="sentence-transformers/all-MiniLM-L6-v2"
    )
    return embedding                   

# Create a connection pool for better performance
# Reuses connections instead of creating new ones for each request
connection_pool = pool.SimpleConnectionPool(
    1,  # minimum connections
    10,  # maximum connections
    user=os.environ.get("SUPABASE_USER"),
    password=os.environ.get("SUPABASE_PASSWORD"),
    host=os.environ.get("SUPABASE_HOST"),
    port=os.environ.get("SUPABASE_PORT"),
    database=os.environ.get("SUPABASE_DB")
)

def connect():
    conn = connection_pool.getconn()
    cursor = conn.cursor()
    return conn, cursor

def release_connection(conn):
    connection_pool.putconn(conn)



# Lazy-loaded embedding cache (~47 MB for 31K verses)
# Loaded in background after frontend triggers /api/cache
cached_ids = None
cached_embeddings = None
cached_norms = None
cache_ready = False
cache_loading = False

def load_embeddings_background():
    global cached_ids, cached_embeddings, cached_norms, cache_ready
    conn, cursor = connect()
    try:
        cursor.execute("SELECT id, embedding FROM embeddings_table")
        rows = cursor.fetchall()
        cached_ids = np.array([int(r[0]) for r in rows], dtype=np.int32)
        cached_embeddings = np.array([
            np.array(r[1].strip("[]").split(','), dtype=np.float32)
            for r in rows
        ], dtype=np.float32)
        cached_norms = np.linalg.norm(cached_embeddings, axis=1)
        cache_ready = True
        print(f"Cached {len(cached_ids)} embeddings in memory")
    finally:
        cursor.close()
        release_connection(conn)

app = Flask(__name__)

@app.route('/')
def home():
    return render_template("3d.html")

@app.route('/api/cache', methods=['POST'])
def trigger_cache():
    global cache_loading
    if cache_ready:
        return jsonify({"status": "already_cached"}), 200
    if cache_loading:
        return jsonify({"status": "already_loading"}), 200
    cache_loading = True
    threading.Thread(target=load_embeddings_background, daemon=True).start()
    return jsonify({"status": "caching_started"}), 200

@app.route('/api/verses', methods=['GET'])
def get_initial_verses():
    conn = cursor = None
    try:
        conn, cursor = connect()
        cursor.execute("""
            SELECT id, embedding
            FROM embeddings_3d_table
        """)

        rows = cursor.fetchall()
        embeddings_3d = [np.array(r[1].strip("[]").split(','), dtype=np.float32) for r in rows]
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
        if cursor: cursor.close()
        if conn: release_connection(conn)

@app.route('/api/verse/<int:verse_id>', methods=['GET'])
def get_verse(verse_id):
    conn = cursor = None
    try:
        conn, cursor = connect()
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
        if cursor: cursor.close()
        if conn: release_connection(conn)

@app.route('/find_similar', methods=['POST'])
def find_similar():
    try:
        id = int(request.json.get('id'))
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid verse ID"}), 400

    print(f"Finding similar verses for ID: {id}")

    conn = cursor = None
    try:
        conn, cursor = connect()
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
        if cursor: cursor.close()
        if conn: release_connection(conn)

@app.route('/find_query', methods=['POST'])
def find_query():
    query = request.json.get('query')
    if not query or not isinstance(query, str):
        return jsonify({"error": "Invalid query"}), 400
    # Wait for cache to be ready if it's still loading
    while not cache_ready:
        import time
        time.sleep(0.1)

    embedding = get_embedding(query)

    # Use cached embeddings and pre-computed norms
    similarities = np.dot(cached_embeddings, embedding) / (
        cached_norms * np.linalg.norm(embedding)
    )

    top_indices = np.argsort(similarities)[-30:][::-1]
    top_ids = cached_ids[top_indices]
    top_similarities = similarities[top_indices]

    # Only hit DB for the 30 verse details
    top_ids_list = [int(vid) for vid in top_ids]
    conn = cursor = None
    try:
        conn, cursor = connect()
        cursor.execute("""
            SELECT id, citation, text
            FROM verses_table
            WHERE id = ANY(%s)
        """, (top_ids_list,))

        verse_dict = {row[0]: {"citation": row[1], "text": row[2]} for row in cursor.fetchall()}

        verse_results = []
        for i, verse_id in enumerate(top_ids_list):
            if verse_id in verse_dict:
                verse_results.append({
                    "id": verse_id,
                    "similarity": float(top_similarities[i]),
                    "citation": verse_dict[verse_id]["citation"],
                    "text": verse_dict[verse_id]["text"]
                })

        return jsonify({"results": verse_results}), 200

    except Exception as e:
        print(f"Error fetching similar verses: {e}")
        return jsonify({"error": "Error fetching similar verses"}), 500

    finally:
        if cursor: cursor.close()
        if conn: release_connection(conn)



if __name__ == '__main__':
    app.run(host="127.0.0.1", port=PORT)

    