from flask import Flask, render_template, request, jsonify
import pandas as pd
import numpy as np
import os
from dotenv import load_dotenv
import psycopg2 

# Load environment variables from .env file
load_dotenv()

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
    return render_template("index.html")

@app.route('/find_similar', methods=['POST'])
def find_similar():
    id = request.json.get('id')
    id = int(id)

    print(id)
    
    conn, cursor = connect()

    try:
        cursor.execute("""
            SELECT similar_id, rank, similarity
            FROM each_verse_similarity_table
            WHERE verse_id = %s 
            ORDER BY rank
            LIMIT 20;
        """, (id,))

        similar_ids = []
        similarities = []
        for row in cursor.fetchall():
            print(row)
            similar_ids.append(int(row[0]))
            similarities.append(float(row[2]))

        verses_results = []

        cursor.execute("""
            SELECT citation, text
            FROM verses_table
            WHERE id = %s;
        """, (id,))

        citation, text = cursor.fetchone()

        verses_results.append({
            "id": id,
            "citation": citation,
            "text": text,
            "similarity": 1.0
        })

        for i, similar_id in enumerate(similar_ids):

            cursor.execute("""
                SELECT citation, text
                FROM verses_table
                WHERE id = %s;
            """, (similar_id,))

            citation, text = cursor.fetchone()

            verses_results.append({
                "id": similar_id,
                "citation": citation,
                "text": text,
                "similarity": similarities[i]
            })
        
        return jsonify({"results": verses_results})

    except Exception as e:
        print(f"Error fetching similar verses: {e}")
        return jsonify({"error": "Error fetching similar verses"}), 500

    finally:
        cursor.close()
        conn.close()
    
    return


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)