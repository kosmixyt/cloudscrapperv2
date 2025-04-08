from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import delete

SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///./sql_app.db"

engine = create_async_engine(SQLALCHEMY_DATABASE_URL, echo=True)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

async def get_db():
    """Dependency for getting DB session."""
    db = AsyncSessionLocal()
    try:
        yield db
    finally:
        await db.close()

async def clear_chrome_sessions():
    """Clear all Chrome sessions from the database at startup."""
    async with AsyncSessionLocal() as session:
        from app.models import ChromeSession  # Import here to avoid circular import
        await session.execute(delete(ChromeSession))
        await session.commit()
        print("All Chrome sessions have been cleared from the database")

async def init_db():
    """Initialize the database and clear Chrome sessions."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await clear_chrome_sessions()
