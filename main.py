from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.exceptions import HTTPException as StarletteHTTPException
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from app.database import engine, init_db
from app.models import Base
from app.routes import router
import nest_asyncio
import asyncio
import platform
import sys
import uvicorn
from dotenv import load_dotenv
import os
from aiohttp import web
import threading
import yaml
import logging
from pathlib import Path
from contextlib import asynccontextmanager

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# Configure the correct event loop policy
if platform.system() == "Windows":
    if sys.version_info >= (3, 8):
        # Use the WindowsSelectorEventLoopPolicy to avoid NotImplementedError
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Apply nest_asyncio to allow nested event loops
nest_asyncio.apply()

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

# Load OpenAPI spec from YAML file if it exists
swagger_yaml_path = os.path.join(os.path.dirname(__file__), "swagger.yaml")
openapi_schema = None
if os.path.exists(swagger_yaml_path):
    with open(swagger_yaml_path, "r") as file:
        openapi_schema = yaml.safe_load(file)

# Define lifespan context manager (replacement for on_event)
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup code (formerly in on_event("startup"))
    logger.info("Starting up application...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await init_db()
    logger.info(f"Static directory exists: {os.path.exists(str(static_dir))}")
    logger.info(f"Static directory contents: {os.listdir(str(static_dir))}")
    logger.info(f"Swagger UI available at: http://0.0.0.0:8000/api/docs")
    logger.info(f"ReDoc available at: http://0.0.0.0:8000/api/redoc")
    
    yield  # This is where the application runs
    
    # Shutdown code (formerly in on_event("shutdown"))
    logger.info("Shutting down application...")

# Initialize FastAPI with lifespan
app = FastAPI(
    title="CloudScrapper API",
    description="An API for browser automation and web scraping with Cloudflare bypass capabilities",
    version="1.0.0",
    openapi_url="/api/openapi.json",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan
)

# Override the OpenAPI schema with our custom schema
if openapi_schema:
    def custom_openapi():
        return openapi_schema
    app.openapi = custom_openapi

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes with a prefix
app.include_router(router, prefix="/api")

# Custom exception handler for 404 errors
@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request, exc):
    logger.info(f"Handling exception: {exc.status_code} for path {request.url.path}")
    
    if exc.status_code == 404:
        # For API routes, return JSON error
        if request.url.path.startswith("/api/"):
            return {"detail": "Not Found"}
        
        # For non-API routes, try to serve index.html
        try:
            index_html_path = os.path.join(static_dir, "index.html")
            if os.path.exists(index_html_path):
                with open(index_html_path, "r") as f:
                    content = f.read()
                return HTMLResponse(content=content)
            else:
                return HTMLResponse(content="<html><body><h1>404 Not Found</h1><p>The static file could not be found.</p></body></html>", status_code=404)
        except Exception as e:
            logger.error(f"Error serving index.html: {str(e)}")
            return HTMLResponse(content=f"<html><body><h1>Error</h1><p>{str(e)}</p></body></html>", status_code=500)
    
    # For other errors, use default exception handling
    raise exc

# Mount static files directory
try:
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")
    logger.info(f"Mounted static files directory: {static_dir}")
except Exception as e:
    logger.error(f"Error mounting static files: {str(e)}")

# Mount static files directory for screenshots
if os.path.exists("screenshot"):
    app.mount("/screenshots", StaticFiles(directory="screenshot"), name="screenshots")

# Simple API health check endpoint
@app.get("/api/healthcheck")
async def healthcheck():
    return {"status": "ok", "message": "Server is running"}

def run_fastapi():
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)

async def main():
    # Démarrer FastAPI dans un thread séparé pour ne pas bloquer
    fastapi_thread = threading.Thread(target=run_fastapi)
    fastapi_thread.daemon = True
    fastapi_thread.start()
    
    # Garder le programme principal en vie
    try:
        while True:
            await asyncio.sleep(3600)  # Vérifier toutes les heures
    except KeyboardInterrupt:
        print("Shutting down servers...")

if __name__ == "__main__":
    # Fix the uvicorn command to pass the application as an import string
    logger.info("Starting server...")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)