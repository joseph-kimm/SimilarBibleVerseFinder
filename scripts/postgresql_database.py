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
    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
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

        '''
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
        '''

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS embeddings_3d_table (
                id INTEGER PRIMARY KEY REFERENCES verses_table(id) ON DELETE CASCADE,
                embedding VECTOR(3)
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

    print("Filling Bible Database...")

    bible_data_path = os.path.join(parent_dir, "datasets", "bible_data.csv")
    bible_data = pd.read_csv(bible_data_path)

    bible_list = []

    print(f"Processing {len(bible_data)} verses...")
    for idx, row in bible_data.iterrows():
        bible_list.append((
            int(row['id']),
            row['citation'],
            row['book'],
            int(row['book_number']),
            int(row['chapter']),
            int(row['verse']),
            row['text']
        ))
        if (idx + 1) % 5000 == 0:
            print(f"  Processed {idx + 1}/{len(bible_data)} verses...")

    conn, cursor = connect()

    try:
        total_rows = len(bible_list)
        batch_size = 1000

        for i in range(0, total_rows, batch_size):
            batch = bible_list[i:i + batch_size]
            psycopg2.extras.execute_batch(
                cursor,
                "INSERT INTO verses_table (id, citation, book, book_number, chapter, verse, text) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                batch,
                page_size=1000
            )
            print(f"  Inserted {min(i + batch_size, total_rows)}/{total_rows} records...")

        conn.commit()
        print("Bible data inserted successfully.")

    except Exception as e:
        print(f"Error inserting data in verses: {e}")
        conn.rollback()

    finally:
        cursor.close()
        conn.close()

    return

def fill_embedding_database():

    print("Filling Embedding Database...")

    embedding_path = os.path.join(parent_dir, "datasets", "bible_embeddings.npz")
    embedding_data = np.load(embedding_path)

    embedding = embedding_data['embeddings']
    ids = embedding_data['ids']

    embedding_list = []

    print(f"Processing {len(ids)} embeddings...")
    for idx, (id_val, emb) in enumerate(zip(ids, embedding)):
        embedding_list.append((int(id_val), emb.tolist()))
        if (idx + 1) % 5000 == 0:
            print(f"  Processed {idx + 1}/{len(ids)} embeddings...")

    conn, cursor = connect()

    try:
        total_rows = len(embedding_list)
        batch_size = 1000

        for i in range(0, total_rows, batch_size):
            batch = embedding_list[i:i + batch_size]
            psycopg2.extras.execute_batch(
                cursor,
                "INSERT INTO embeddings_table (id, embedding) VALUES (%s, %s)",
                batch,
                page_size=1000
            )
            print(f"  Inserted {min(i + batch_size, total_rows)}/{total_rows} records...")

        conn.commit()
        print("Embedding data inserted successfully.")

    except Exception as e:
        print(f"Error inserting data in embeddings using execute_batch: {e}")
        conn.rollback()

    finally:
        cursor.close()
        conn.close()

    return

def fill_similarity_database():
    print("Filling Similarity Database...")

    each_verse_similarity = os.path.join(parent_dir, "datasets", "bible_similar_each_verse.npz")
    each_verse_data = np.load(each_verse_similarity)

    ids = each_verse_data['ids']
    top_verses = each_verse_data['top_verses']
    top_scores = each_verse_data['top_scores']

    each_verse_flatten = []

    print(f"Processing {len(ids)} verses with their similar verses...")
    for i, verse_id in enumerate(ids):
        for rank in range(len(top_verses[i])):
            each_verse_flatten.append((
                int(verse_id),
                int(top_verses[i][rank]),
                rank + 1,
                float(top_scores[i][rank])
            ))
        if (i + 1) % 5000 == 0:
            print(f"  Processed {i + 1}/{len(ids)} verses (Total records: {len(each_verse_flatten)})...")

    print(f"Total similarity records to insert: {len(each_verse_flatten)}")

    conn, cursor = connect()

    try:
        total_rows = len(each_verse_flatten)
        batch_size = 1000

        for i in range(0, total_rows, batch_size):
            batch = each_verse_flatten[i:i + batch_size]
            psycopg2.extras.execute_batch(
                cursor,
                "INSERT INTO each_verse_similarity_table (verse_id, similar_id, rank, similarity) VALUES (%s, %s, %s, %s)",
                batch,
                page_size=1000
            )
            print(f"  Inserted {min(i + batch_size, total_rows)}/{total_rows} records...")

        conn.commit()
        print("Each verse similarity data inserted successfully.")

    except Exception as e:
        print(f"Error inserting data in embeddings using execute_batch: {e}")
        conn.rollback()

    finally:
        cursor.close()
        conn.close()

    return

def fill_overall_similarity_database():
    print("Filling Overall Similarity Database...")

    overall_verse_similarity = os.path.join(parent_dir, "datasets", "bible_similar_top_million.npz")
    overall_verse_data = np.load(overall_verse_similarity)

    engine = create_engine(os.getenv("DATABASE_URL"))

    id1 = overall_verse_data['id1']
    id2 = overall_verse_data['id2']
    scores = overall_verse_data['scores']

    overall_data_list = []

    print(f"Processing {len(id1)} similarity records...")
    for i in range(len(id1)):
        overall_data_list.append(
            (int(id1[i]), int(id2[i]), i+1, float(scores[i]))
        )
        if (i + 1) % 100000 == 0:
            print(f"  Processed {i + 1}/{len(id1)} records...")

    conn, cursor = connect()

    try:
        total_rows = len(overall_data_list)
        batch_size = 1000

        for i in range(0, total_rows, batch_size):
            batch = overall_data_list[i:i + batch_size]
            psycopg2.extras.execute_batch(
                cursor,
                "INSERT INTO overall_verse_similarity_table (id1, id2, rank, similarity) VALUES (%s, %s, %s, %s)",
                batch,
                page_size=1000
            )
            print(f"  Inserted {min(i + batch_size, total_rows)}/{total_rows} records...")

        conn.commit()
        print("Overall verse similarity data inserted successfully.")

    except Exception as e:
        print(f"Error inserting data in verses: {e}")
        conn.rollback()

    finally:
        cursor.close()
        conn.close()

    return

def fill_3d_embedding_database():
    print("Filling 3D Embedding Database...")

    embedding_3d_path = os.path.join(parent_dir, "datasets", "bible_embeddings_3d.npz")
    embedding_3d_data = np.load(embedding_3d_path)

    embedding_3d = embedding_3d_data['embeddings']
    ids = embedding_3d_data['ids']

    embedding_3d_list = []

    print(f"Processing {len(ids)} 3D embeddings...")
    for idx, (id_val, emb) in enumerate(zip(ids, embedding_3d)):
        embedding_3d_list.append((int(id_val), emb.tolist()))
        if (idx + 1) % 5000 == 0:
            print(f"  Processed {idx + 1}/{len(ids)} 3D embeddings...")

    conn, cursor = connect()

    try:
        total_rows = len(embedding_3d_list)
        batch_size = 1000

        for i in range(0, total_rows, batch_size):
            batch = embedding_3d_list[i:i + batch_size]
            psycopg2.extras.execute_batch(
                cursor,
                "INSERT INTO embeddings_3d_table (id, embedding) VALUES (%s, %s)",
                batch,
                page_size=1000
            )
            print(f"  Inserted {min(i + batch_size, total_rows)}/{total_rows} records...")

        conn.commit()
        print("3D Embedding data inserted successfully.")

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

        cursor.execute("SELECT COUNT(*) FROM embeddings_3d_table;")
        count = cursor.fetchone()[0]
        print(f"Number of records in embeddings_3d_table: {count}") 
        
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
            CREATE INDEX idx_each_verse_verse_id ON each_verse_similarity_table(verse_id)
        """)

        conn.commit()
        
    except Exception as e:
        print(f"Error creating index: {e}")
        conn.rollback()

    finally:
        cursor.close()
        conn.close()

    return


if __name__ == "__main__":
    fill_similarity_database()
    fill_3d_embedding_database()
    create_indexes()
    

