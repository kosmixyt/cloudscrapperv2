from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
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

load_dotenv()
# Configure the correct event loop policy
if platform.system() == "Windows":
    if sys.version_info >= (3, 8):
        # Use the WindowsSelectorEventLoopPolicy to avoid NotImplementedError
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Apply nest_asyncio to allow nested event loops
nest_asyncio.apply()

# Load OpenAPI spec from YAML file if it exists
swagger_yaml_path = os.path.join(os.path.dirname(__file__), "swagger.yaml")
openapi_schema = None
if os.path.exists(swagger_yaml_path):
    with open(swagger_yaml_path, "r") as file:
        openapi_schema = yaml.safe_load(file)

app = FastAPI(
    title="CloudScrapper API",
    description="An API for browser automation and web scraping with Cloudflare bypass capabilities",
    version="1.0.0",
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc"
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

app.include_router(router, prefix="")

# Mount static files directory for screenshots
if os.path.exists("screenshot"):
    app.mount("/screenshots", StaticFiles(directory="screenshot"), name="screenshots")

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await init_db()
    print(f"Swagger UI available at: http://0.0.0.0:8000/docs")
    print(f"ReDoc available at: http://0.0.0.0:8000/redoc")


@app.on_event("shutdown")
async def shutdown():
    pass

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
    asyncio.run(main())