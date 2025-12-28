from pathlib import Path
import sys

from dotenv import load_dotenv

backend_dir = Path(__file__).resolve().parent.parent / "backend"

sys.path.append(str(backend_dir))

load_dotenv(".env.backend")

from app.main import app
import json

def export_openapi(location: str):
    openapi_schema = app.openapi()
    with open(location, "w") as f:
        json.dump(openapi_schema, f, indent=2)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: ./extract_docs.py <output_path>")
        sys.exit(1)
    export_openapi(sys.argv[1])