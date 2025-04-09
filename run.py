import os
import uvicorn
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Ensure static directory exists
static_dir = Path(__file__).parent / "static"
if not static_dir.exists():
    logger.info(f"Creating static directory: {static_dir}")
    static_dir.mkdir(parents=True)

# Ensure index.html exists
index_path = static_dir / "index.html"
if not index_path.exists():
    logger.warning(f"index.html not found at {index_path}, creating a simple one")
    with open(index_path, "w") as f:
        f.write("""<!DOCTYPE html>
<html>
<head>
    <title>CloudScrapper</title>
</head>
<body>
    <h1>CloudScrapper</h1>
    <p>Welcome to CloudScrapper!</p>
</body>
</html>""")

if __name__ == "__main__":
    logger.info("Starting server...")
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
