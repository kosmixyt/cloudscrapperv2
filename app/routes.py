from fastapi import APIRouter, Depends, HTTPException, status, Body, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import timedelta
from app.database import AsyncSessionLocal
import os
from app import models, schemas
from app.auth import (
    get_password_hash, 
    verify_password, 
    create_access_token, 
    get_current_user,
    ACCESS_TOKEN_EXPIRE_MINUTES
)
from fastapi import Request, Response
from app.api.flaresolver import flaresolverRoute
from app.api.allowedHost import create_allowed_host, delete_allowed_host, get_user_allowed_hosts
import nodriver as uc
import threading
from typing import List, Dict, Any
import httpx
from urllib.parse import urljoin
import asyncio
import uuid
from contextlib import asynccontextmanager
import time

router = APIRouter()

# Task storage for background tasks
task_results = {}
task_status = {}

# Background task function
async def process_flaresolver_request(task_id: str, data: Dict[str, Any], client_ip: str, db: AsyncSession):
    try:
        task_status[task_id] = "processing"
        result = await flaresolverRoute(data, client_ip, db)
        task_results[task_id] = result
        task_status[task_id] = "completed"
    except Exception as e:
        task_results[task_id] = {"error": str(e)}
        task_status[task_id] = "failed"

# Session manager for background tasks
@asynccontextmanager
async def get_db_for_background():
    db = AsyncSessionLocal()
    try:
        yield db
    finally:
        await db.close()

async def get_db():
    db = AsyncSessionLocal()
    try:
        yield db
    finally:
        await db.close()


@router.post("/users/", response_model=schemas.User)
async def create_user(user: schemas.UserCreate, db: AsyncSession = Depends(get_db)):
    if os.getenv("DISABLE_REGISTRATION") == "true":
        raise HTTPException(status_code=403, detail="Registration is disabled")
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
    return {"message": "Successfully logged out"}

@router.get("/protected", response_model=schemas.User)
async def protected_route(current_user: models.User = Depends(get_current_user)):
    return current_user

@router.post("/v1")
async def flaresolver(
    request: Request, 
    # background_tasks: BackgroundTasks,
    data: Dict[str, Any] = Body(...),  
    db: AsyncSession = Depends(get_db)
):
    task_id = str(uuid.uuid4())
    task_status[task_id] = "queued"
    
    threading.Thread(
        target=asyncio.run,
        args=(process_flaresolver_request(task_id, data, request.client.host, db),)
    ).start()
    
    
    return {
        "task_id": task_id,
        "status": "queued",
        "message": "Your request is being processed in the background"
    }

@router.get("/v1/tasks/{task_id}")
async def get_task_status(
    task_id: str, 
    wait: bool = False, 
    timeout: int = 30,
    polling_interval: float = 0.5
):
    if task_id not in task_status:
        raise HTTPException(status_code=404, detail="Task not found")
    
    status = task_status[task_id]
    
    # If wait=True and task is still processing, poll until completion or timeout
    if wait and status in ["queued", "processing"]:
        start_time = time.time()
        while status in ["queued", "processing"] and (time.time() - start_time) < timeout:
            # Wait for a short interval before checking again
            await asyncio.sleep(polling_interval)
            
            # Check if task still exists
            if task_id not in task_status:
                raise HTTPException(status_code=404, detail="Task not found")
            
            # Update status
            status = task_status[task_id]
    
    # Return result if task is completed/failed
    if status == "completed" or status == "failed":
        result = task_results.get(task_id, {"error": "Result not found"})
        
        # Optionally clean up completed tasks after retrieval
        if task_id in task_results:
            del task_results[task_id]
            del task_status[task_id]
            
        return {
            "task_id": task_id,
            "status": status,
            "result": result
        }
    
    # If still processing after wait timeout, return current status
    return {
        "task_id": task_id,
        "status": status
    }

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

@router.get("/requests/", response_model=List[schemas.Request])
async def get_user_requests(
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    result = await db.execute(select(models.Request).where(models.Request.user_id == current_user.id))
    return result.scalars().all()

@router.get("/screenshots/{request_id}", response_class=FileResponse)
async def get_request_screenshot(
    request_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # Get the request and check if it belongs to the current user
    result = await db.execute(select(models.Request).where(models.Request.id == request_id))
    request = result.scalar_one_or_none()
    
    if not request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Request not found"
        )
    
    if request.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to view this screenshot"
        )
    
    if not request.screenShotName:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No screenshot available for this request"
        )
    
    # Construct the path to the screenshot
    screenshot_path = os.path.join(os.getenv("SCREENSHOT_DIR"), request.screenShotName)
    
    if not os.path.exists(screenshot_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Screenshot file not found"
        )
    
    return FileResponse(screenshot_path)

@router.get("/chrome-sessions/", response_model=List[schemas.ChromeSession])
async def get_user_chrome_sessions(
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    result = await db.execute(select(models.ChromeSession).where(models.ChromeSession.user_id == current_user.id))
    return result.scalars().all()
