import psycopg2
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def test_connection():
    try:
        # Connect using connection string from .env
        conn = psycopg2.connect(os.getenv('DATABASE_URL'))
        cursor = conn.cursor()
        
        # Test basic query
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        print(f"✅ Connected successfully!")
        print(f"PostgreSQL version: {version[0]}")
        
        # Test pgvector extension
        cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        cursor.execute("SELECT * FROM pg_extension WHERE extname = 'vector';")
        vector_ext = cursor.fetchone()
        
        if vector_ext:
            print("✅ pgvector extension is available!")
        else:
            print("❌ pgvector extension not found")
        
        cursor.close()
        conn.close()
        print("✅ Connection test completed successfully!")
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("\nTroubleshooting tips:")
        print("1. Make sure Docker container is running: docker ps")
        print("2. Check container logs: docker-compose logs postgres")
        print("3. Verify .env file has correct credentials")

if __name__ == "__main__":
    test_connection()