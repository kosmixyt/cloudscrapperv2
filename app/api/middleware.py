from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Vous pouvez ajouter ici votre logique de middleware
        # Par exemple, vérification de l'authentification
        
        response = await call_next(request)
        return response

class CORSMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        # Ajouter les headers CORS nécessaires
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        
        return response
