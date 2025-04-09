from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.exceptions import HTTPException as StarletteHTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
import logging
from app.routes import router

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="CloudScrapper API")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define static directory path
static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")

# Ensure the static directory exists
if not os.path.exists(static_dir):
    os.makedirs(static_dir)
    logger.info(f"Created static directory at {static_dir}")

# Log static directory path for debugging
logger.info(f"Static files directory: {static_dir}")
logger.info(f"Static directory exists: {os.path.exists(static_dir)}")
logger.info(f"Static directory contents: {os.listdir(static_dir)}")

# Include API routes with a prefix
app.include_router(router, prefix="/api")

# Mount the static files directory
try:
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
    logger.info("Successfully mounted static files directory")
except Exception as e:
    logger.error(f"Error mounting static files: {str(e)}")

# Custom exception handler for 404 errors
@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    logger.info(f"Handling exception: {exc.status_code} for path {request.url.path}")
    
    if exc.status_code == 404:
        # For API routes, return JSON error
        if request.url.path.startswith("/api/"):
            return JSONResponse(
                status_code=404, 
                content={"detail": "Not Found"}
            )
        
        # For non-API routes, try to serve index.html
        try:
            index_path = os.path.join(static_dir, "index.html")
            logger.info(f"Trying to serve index.html from {index_path}")
            logger.info(f"Index file exists: {os.path.exists(index_path)}")
            
            if os.path.exists(index_path):
                with open(index_path, "r") as f:
                    content = f.read()
                return HTMLResponse(content=content)
            else:
                logger.error(f"index.html not found at {index_path}")
                return HTMLResponse(content="<html><body><h1>404 Not Found</h1><p>The static file could not be found.</p></body></html>", status_code=404)
        except Exception as e:
            logger.error(f"Error serving index.html: {str(e)}")
            return HTMLResponse(content=f"<html><body><h1>Error</h1><p>{str(e)}</p></body></html>", status_code=500)
    
    # For other errors, use default exception handling
    raise exc

# Simple root path to check if the server is running
@app.get("/api/healthcheck")
async def healthcheck():
    return {"status": "ok", "message": "Server is running"}
