import psycopg2
import psycopg2.extras
import os
from dotenv import load_dotenv
import numpy as np
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool

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

# creating database schemas
def setup_database():
    conn, cursor = connect()
    
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
                PRIMARY KEY(verse_id, similar_id)
            );
        """)

        # Create table storing most similar verses globally
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS overall_verse_similarity_table (
                id1 INTEGER REFERENCES verses_table(id) ON DELETE CASCADE,
                id2 INTEGER REFERENCES verses_table(id) ON DELETE CASCADE,
                rank INTEGER,
                similarity FLOAT,
                PRIMARY KEY(rank)
            );
        """)
        
        # Commit all changes
        conn.commit()
        print("Tables created successfully.")
        
    except Exception as e:
        print(f"Error setting up database: {e}")
        conn.rollback()
    
    finally:
        cursor.close()
        conn.close()

    return

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)

def fill_bible_database():

    bible_data_path = os.path.join(parent_dir, "datasets", "bible_data.csv")
    bible_data = pd.read_csv(bible_data_path)

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

    with engine.begin() as conn: 
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
            raise

    return

def fill_embedding_database():

    embedding_path = os.path.join(parent_dir, "datasets", "bible_embeddings.npz")
    embedding_data = np.load(embedding_path)

    embedding = embedding_data['embeddings']
    ids = embedding_data['ids']

    embedding_list = []

    for id_val, emb in zip(ids, embedding):
        embedding_list.append((int(id_val), emb.tolist()))

    conn, cursor = connect()

    try:
        psycopg2.extras.execute_batch(
            cursor,
            "INSERT INTO embeddings_table (id, embedding) VALUES (%s, %s)",
            embedding_list,
            page_size=1000
        )

        conn.commit()

    except Exception as e:
        print(f"Error inserting data in embeddings using execute_batch: {e}")
        conn.rollback()

    finally:
        cursor.close()
        conn.close()

    return

def fill_similarity_database():

    each_verse_similarity = os.path.join(parent_dir, "datasets", "bible_similar_each_verse.npz")
    each_verse_data = np.load(each_verse_similarity)

    ids = each_verse_data['ids']
    top_verses = each_verse_data['top_verses']
    top_scores = each_verse_data['top_scores']

    each_verse_flatten = []

    for i, verse_id in enumerate(ids):
        for rank in range(len(top_verses[i])):
            each_verse_flatten.append((
                int(verse_id),
                int(top_verses[i][rank]),
                rank + 1,
                float(top_scores[i][rank])
            ))
            
    conn, cursor = connect()

    try:
        psycopg2.extras.execute_batch(
            cursor,
            "INSERT INTO each_verse_similarity_table (verse_id, similar_id, rank, similarity) VALUES (%s, %s, %s, %s)",
            each_verse_flatten,
            page_size=1000
        )

        conn.commit()

    except Exception as e:
        print(f"Error inserting data in embeddings using execute_batch: {e}")
        conn.rollback()

    finally:
        cursor.close()
        conn.close()

    return

def fill_overall_similarity_database():

    overall_verse_similarity = os.path.join(parent_dir, "datasets", "bible_similar_top_million.npz")
    overall_verse_data = np.load(overall_verse_similarity)

    engine = create_engine(os.getenv("DATABASE_URL"))

    id1 = overall_verse_data['id1']
    id2 = overall_verse_data['id2']
    scores = overall_verse_data['scores']

    overall_data_list = []

    for i in range(len(id1)):
        overall_data_list.append(
            (int(id1[i]), int(id2[i]), i+1, float(scores[i]))
        )

    conn, cursor = connect()

    try:
        psycopg2.extras.execute_batch(
            cursor,
            "INSERT INTO overall_verse_similarity_table (id1, id2, rank, similarity) VALUES (%s, %s, %s, %s)",
            overall_data_list,
            page_size=1000
        )

        conn.commit()

    except Exception as e:
        print(f"Error inserting data in embeddings using execute_batch: {e}")
        conn.rollback()

    finally:
        cursor.close()
        conn.close()
    
    return

def check_database_filled():
    conn, cursor = connect()

    try:
        cursor.execute("SELECT COUNT(*) FROM verses_table;")
        count = cursor.fetchone()[0]
        print(f"Number of records in verses_table: {count}")

        cursor.execute("SELECT COUNT(*) FROM embeddings_table;")
        count = cursor.fetchone()[0]
        print(f"Number of records in embeddings_table: {count}")

        cursor.execute("SELECT COUNT(*) FROM each_verse_similarity_table;")
        count = cursor.fetchone()[0]
        print(f"Number of records in each_verse_similarity_table: {count}")

        cursor.execute("SELECT COUNT(*) FROM overall_verse_similarity_table;")
        count = cursor.fetchone()[0]
        print(f"Number of records in overall_verse_similarity_table: {count}")

    except Exception as e:
        print(f"Error checking database: {e}")
        return False

    finally:
        cursor.close()
        conn.close()

    return

def create_indexes():
    
    conn, cursor = connect()

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
        conn.rollback()

    finally:
        cursor.close()
        conn.close()

    return

def check_indexes():

    conn, cursor = connect()

    try:
        cursor.execute("""
            SELECT 
                schemaname,
                tablename,
                indexname,
                indexdef
            FROM pg_indexes
            ORDER BY schemaname, tablename, indexname;
        """)

        results = cursor.fetchall()

        for row in results:
            print(row)

    except Exception as e:
        print(f"Error checking index: {e}")

    finally:
        cursor.close()
        conn.close()

    return

if __name__ == "__main__":
    check_indexes()
    