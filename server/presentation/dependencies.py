"""FastAPI dependency injection — auth and container access."""
from __future__ import annotations
from fastapi import Request, HTTPException, Depends
from server.domain.entities.pairing import SessionToken

def get_container(request: Request):
    return request.app.state.container

async def verify_token(request: Request) -> SessionToken:
    # Extract from Authorization header or query param
    auth = request.headers.get("Authorization", "")
    token_str = ""
    if auth.startswith("Bearer "):
        token_str = auth[7:]
    elif "token" in request.query_params:
        token_str = request.query_params["token"]
    
    if not token_str:
        raise HTTPException(status_code=401, detail="Missing authentication token")
    
    client_ip = request.client.host if request.client else None
    container = request.app.state.container
    token = SessionToken(value=token_str)
    if not container.token_store.verify(token, client_ip=client_ip):
        raise HTTPException(status_code=401, detail="Invalid session token")
    return token
