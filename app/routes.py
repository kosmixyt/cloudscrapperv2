from fastapi import APIRouter, Depends, HTTPException, status, Body
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import timedelta
from app.database import AsyncSessionLocal
from app import models, schemas
from app.auth import (
    get_password_hash, 
    verify_password, 
    create_access_token, 
    get_current_user,
    ACCESS_TOKEN_EXPIRE_MINUTES
)
from fastapi import Request
from app.api.flaresolver import flaresolverRoute
from app.api.allowedHost import create_allowed_host, delete_allowed_host, get_user_allowed_hosts
import nodriver as uc
from typing import List, Dict, Any

router = APIRouter()

async def get_db():
    db = AsyncSessionLocal()
    try:
        yield db
    finally:
        await db.close()

@router.post("/users/", response_model=schemas.User)
async def create_user(user: schemas.UserCreate, db: AsyncSession = Depends(get_db)):
    # Check if user already exists
    result = await db.execute(select(models.User).where(models.User.email == user.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = get_password_hash(user.password)
    db_user = models.User(
        email=user.email,
        full_name=user.full_name,
        hashed_password=hashed_password
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user

@router.post("/login", response_model=schemas.Token)
async def login(form_data: schemas.LoginData, db: AsyncSession = Depends(get_db)):
    # Find user by email
    result = await db.execute(select(models.User).where(models.User.email == form_data.email))
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/logout")
async def logout():
    # Since JWT is stateless, we don't need to do anything server-side
    # The client should remove the token from their storage
    return {"message": "Successfully logged out"}

@router.get("/protected", response_model=schemas.User)
async def protected_route(current_user: models.User = Depends(get_current_user)):
    return current_user

@router.post("/v1")
async def flaresolver(request: Request, data: Dict[str, Any] = Body(...),  db: AsyncSession = Depends(get_db)):
    return await flaresolverRoute(data, request.client.host, db)
    
@router.post("/allowed-hosts/", response_model=schemas.AllowedOrigin)
async def create_host(
    origin: schemas.AllowedOriginCreate, 
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    return await create_allowed_host(db, origin.origin, current_user.id)

@router.delete("/allowed-hosts/{origin_id}")
async def delete_host(
    origin_id: int, 
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    return await delete_allowed_host(db, origin_id, current_user.id)

@router.get("/allowed-hosts/", response_model=List[schemas.AllowedOrigin])
async def get_hosts(
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    return await get_user_allowed_hosts(db, current_user.id)

@router.get("/users/", response_model=List[schemas.User])
async def read_users(
    skip: int = 0, 
    limit: int = 100, 
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user)  # Protected route
):
    result = await db.execute(select(models.User).offset(skip).limit(limit))
    users = result.scalars().all()
    return users