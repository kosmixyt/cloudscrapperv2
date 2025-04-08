from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi import HTTPException, status
from app import models

async def create_allowed_host(db: AsyncSession, origin: str, user_id: int):
    # Check if origin already exists
    result = await db.execute(select(models.AllowedOrigin).where(models.AllowedOrigin.origin == origin))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Origin already registered")
    
    # Create new allowed host
    db_origin = models.AllowedOrigin(
        origin=origin,
        owner_id=user_id
    )
    db.add(db_origin)
    await db.commit()
    await db.refresh(db_origin)
    return db_origin

async def delete_allowed_host(db: AsyncSession, origin_id: int, user_id: int):
    # Find the origin
    result = await db.execute(select(models.AllowedOrigin).where(models.AllowedOrigin.id == origin_id))
    origin = result.scalar_one_or_none()
    
    if not origin:
        raise HTTPException(status_code=404, detail="Allowed host not found")
    
    # Check if user owns this origin
    if origin.owner_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this origin")
    
    # Delete the origin
    await db.delete(origin)
    await db.commit()
    return {"message": "Origin deleted successfully"}

async def get_user_allowed_hosts(db: AsyncSession, user_id: int):
    result = await db.execute(
        select(models.AllowedOrigin).where(models.AllowedOrigin.owner_id == user_id)
    )
    return result.scalars().all()
