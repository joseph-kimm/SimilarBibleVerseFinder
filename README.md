# Similar Bible Verse Finder

An interactive web app that visualizes all 31,000+ Bible verses as stars in a 3D galaxy. Semantically similar verses cluster together, letting you explore connections across the entire Bible.

[Live Demo](https://bible-verse-explorer-532219653721.asia-northeast1.run.app/)

## How It Works

Each verse is converted into a vector embedding using the `sentence-transformers/all-MiniLM-L6-v2` model. Cosine similarity measures how related verses are in meaning, and UMAP projects them into 3D space for the visualization.

- **Verse Search** - Pick a book, chapter, and verse to find the 30 most similar verses
- **Text Search** - Enter any text to compare against all verses in real time

## Tech Stack

- **Frontend** - HTML/CSS/JS + Three.js
- **Backend** - Flask (Python)
- **Database** - PostgreSQL (Supabase) + pgvector
- **Embeddings** - Hugging Face Inference API
- **Deployment** - Modal

## Project Structure

```
app/        - Frontend and Flask backend
datasets/   - Bible verse data and precomputed embeddings (stored in Supabase)
notebooks/  - Jupyter notebooks for data exploration and processing
scripts/    - Database setup and connection scripts
devops/     - Docker and Google Cloud config (no longer in use)
```

## Setup

1. Create a `.env` file with your Hugging Face token and Supabase credentials
2. Install dependencies: `pip install -r app/requirements.txt`
3. Populate the database: `python scripts/postgresql_database.py`
4. Run the app: `cd app && flask run`

## License

MIT
