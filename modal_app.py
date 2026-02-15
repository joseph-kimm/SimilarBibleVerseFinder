import modal

app = modal.App("bible-verse-explorer")

image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "flask",
        "psycopg2-binary",
        "numpy",
        "pandas",
        "huggingface-hub",
        "python-dotenv",
    )
    .add_local_dir("app", remote_path="/root/app")
)

@app.function(
    image=image,
    secrets=[modal.Secret.from_name("bible-verse-secrets")],
    min_containers=0,
    cpu=2.0,
    memory=1024,
    timeout=300,
)

@modal.wsgi_app()
def flask_app():
    import sys
    sys.path.insert(0, "/root")
    from app.app import app
    return app
