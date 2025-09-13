import psycopg2
import os
from dotenv import load_dotenv
import numpy as np
import pandas as pd
from sqlalchemy import create_engine

# Load environment variables from .env file
load_dotenv()

# creating database schemas
def setup_database():
    conn = psycopg2.connect(
        host=os.getenv("POSTGRES_HOST"),
        dbname=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        port=os.getenv("POSTGRES_PORT")
    )
    cursor = conn.cursor()
    
    try:
        # Enable pgvector extension
        cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        
        # Create verses table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS verses_table (
                id INTEGER PRIMARY KEY,
                citation VARCHAR(50),
                book VARCHAR(50),
                book_number INTEGER,
                chapter INTEGER,
                verse INTEGER,
                text TEXT
            );
        """)

        # Create embeddings table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS embeddings_table (
                id INTEGER PRIMARY KEY REFERENCES verses_table(id) ON DELETE CASCADE,
                embedding VECTOR(384)
            );
        """)

        # Create table storing verses similar to each verse
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS each_verse_similarity_table (
                verse_id INTEGER REFERENCES verses_table(id) ON DELETE CASCADE,
                similar_id INTEGER REFERENCES verses_table(id) ON DELETE CASCADE,
                rank INTEGER,
                similarity FLOAT,
                PRIMARY_KEY (verse_id, similar_id)
            );
        """)

        # Create table storing most similar verses globally
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS overall_verse_similarity_table (
                id1 INTEGER REFERENCES verses_table(id) ON DELETE CASCADE,
                id2 INTEGER REFERENCES versverses_tablees(id) ON DELETE CASCADE,
                rank INTEGER,
                similarity FLOAT,
                PRIMARY_KEY (rank)
            );
        """)
        
        # Commit all changes
        conn.commit()
        print("Tables created ")
        
    except Exception as e:
        print(f"Error setting up database: {e}")
        conn.rollback()
    
    finally:
        cursor.close()
        conn.close()

    return

def fill_database():

    bible_data_path = "../datasets/bible_data.csv"
    embedding_path = "../datasets/bible_embeddings.npz"
    each_verse_similarity = "../datasets/bible_similar_each_verse.npz"
    overall_verse_similarity = "../datasets/bible_similar_top_million.npz"

    # getting data from all csv and npz files
    bible_data = pd.read_csv(bible_data_path)
    embedding_data = np.load(embedding_path)
    each_verse_data = np.load(each_verse_similarity)
    overall_verse_data = np.load(overall_verse_similarity)

    engine = create_engine(os.getenv("DATABASE_URL"))

    # making sure the data types are correct
    bible_df = bible_data.astype({
        "id": "int64",
        "citation": "string",
        "book": "string",
        "book_number": "int64",
        "chapter": "int64",
        "verse": "int64",
        "text": "string"
    })

    # adding bible data into the table
    try:
        bible_df.to_sql(
            name='verses_table',
            con=engine,
            if_exists='append',
            index=False,
            method='multi'
        )

    except Exception as e:
        print(f"Error inserting data in verses: {e}")


    embedding = embedding_data['embeddings']
    ids = embedding_data['ids']

    # changing the npz to a dataframe
    # each row contains id and 384 vector representing the verse text
    embedding_df = pd.DataFrame({
        'id': ids.astype(int),
        'embedding': [emb.tolist() for emb in embedding]
    })

    try:
        embedding_df.to_sql(
            name='embeddings_table',
            con=engine,
            if_exists='append',
            index=False,
            method='multi'
        )

    except Exception as e:
        print(f"Error inserting data in embeddings: {e}")

    ids = each_verse_data['ids']
    top_verses = each_verse_data['top_verses']
    top_scores = each_verse_data['top_scores']

    each_verse_flatten = []

    for i, verse_id in enumerate(ids):
        for rank, in range(len(top_verses[i])):
            each_verse_flatten.append({
                'verse_id': int(verse_id),
                'similar_id': int(top_verses[i][rank]),
                'rank': rank + 1,
                'rank_position': float(top_scores[i][rank])
            })

    each_verse_df = pd.DataFrame(each_verse_flatten)

    try:
        each_verse_df.to_sql(
            name='each_verse_similarity_table',
            con=engine,
            if_exists='append',
            index=False,
            method='multi'
        )

    except Exception as e:
        print(f"Error inserting data in each verse similarity table: {e}")

    id1 = overall_verse_data['id1']
    id2 = overall_verse_data['id2']
    scores = overall_verse_data['scores']

    overall_data_df = pd.DataFrame({
        'id1': id1.astype(int),
        'id2': id2.astype(int),
        'similarity': scores.astpe(float),
        'rank': list(range(1, len(id1)+1))
    })

    try:
        overall_data_df.to_sql(
            name='overall_verse_similarity_table',
            con=engine,
            if_exists='append',
            index=False,
            method='multi'
        )

    except Exception as e:
        print(f"Error inserting data in overall verse similarity table: {e}")
    
    return

def create_indexes():
    conn = psycopg2.connect(
        host=os.getenv("POSTGRES_HOST"),
        dbname=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        port=os.getenv("POSTGRES_PORT")
    )

    cursor = conn.cursor()

    try:
        cursor.execute("""
            CREATE INDEX idx_verses_id ON verses_table(id);        
        """)

        cursor.execute(""" 
            CREATE INDEX IF NOT EXISTS idx_embeddings_vector ON embeddings_table 
            USING ivfflat (embedding vector_cosine_ops) WITH (lists = 50);
        """)

        cursor.execute("""
            CREATE INDEX idx_each_verse_verse_id ON each_verse_similarity_table(verse_id)
        """)

        # because we did the upper triangle, we only need index on id1
        cursor.execute("""
            CREATE INDEX idx_overall_verse_id1 ON overall_verse_similarity_table(id1)
        """)

        conn.commit()
        
    except Exception as e:
        print(f"Error creating index: {e}")

    finally:
        cursor.close()
        conn.close()

    return

if __name__ == "__main__":
    setup_database()