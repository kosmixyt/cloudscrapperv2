from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, init_db
from app.models import Base
import nodriver as uc
from app.routes import router
import nest_asyncio
import asyncio
import platform
import sys

# Configure the correct event loop policy
if platform.system() == "Windows":
    if sys.version_info >= (3, 8):
        # Use the WindowsSelectorEventLoopPolicy to avoid NotImplementedError
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Apply nest_asyncio to allow nested event loops
nest_asyncio.apply()

app = FastAPI(title="FastAPI App")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="")


@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await init_db()
        

if __name__ == "__main__":
    import uvicorn
    
    # Use the event loop with uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)