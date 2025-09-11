import psycopg2
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def setup_database():
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    cursor = conn.cursor()
    
    try:
        # Enable pgvector extension
        cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        
        # Create verses table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS verses (
                id PRIMARY KEY,
                book VARCHAR(100) NOT NULL,
                book_number INTEGER NOT NULL,
                chapter INTEGER NOT NULL,
                verse INTEGER NOT NULL,
                text TEXT NOT NULL,
                embedding VECTOR(384),
            );
        """)
        

        # Create traditional indexes for filtering
        print("📇 Creating traditional indexes...")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS verses_book_idx ON verses (book);
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS verses_book_chapter_idx ON verses (book, chapter);
        """)
        
        # Commit all changes
        conn.commit()
        print("✅ Database schema created successfully!")
        
        # Show table info
        cursor.execute("""
            SELECT column_name, data_type, is_nullable 
            FROM information_schema.columns 
            WHERE table_name = 'verses'
            ORDER BY ordinal_position;
        """)
        
        columns = cursor.fetchall()
        print("\n📊 Table structure:")
        for col_name, data_type, nullable in columns:
            print(f"  {col_name}: {data_type} {'(nullable)' if nullable == 'YES' else ''}")
        
    except Exception as e:
        print(f"❌ Error setting up database: {e}")
        conn.rollback()
    
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    setup_database()