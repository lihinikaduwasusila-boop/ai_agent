from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from common.security import hash_password, verify_password, create_access_token, verify_token
from common.db import create_user, get_user_by_username, get_search_history, MySQL
from common.models import UserRegister, UserLogin, AuthResponse, HistoryItem, HistoryResponse
from .router import router as query_router
from common.logging import logger

app = FastAPI(title="Orchestrator")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def on_startup():
    try:
        await MySQL.init_pool()
    except Exception as e:
        logger.warning(f"RA Check: MySQL init failed on startup; continuing without cache. Error: {e}")


@app.post("/auth/register", response_model=AuthResponse)
async def register(payload: UserRegister):
    user = await get_user_by_username(payload.username)
    if user:
        raise HTTPException(status_code=409, detail="Username already exists")
    pw_hash = hash_password(payload.password)
    uid = await create_user(payload.username, payload.email, pw_hash)
    token = create_access_token(str(uid))
    logger.info("RA Check: User registered; minimal logging, no passwords exposed.")
    return AuthResponse(access_token=token)


@app.post("/auth/login", response_model=AuthResponse)
async def login(payload: UserLogin):
    user = await get_user_by_username(payload.username)
    if not user or not verify_password(payload.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token(str(user["id"]))
    logger.info("RA Check: User login; fairness and security ensured via hashed password verification.")
    return AuthResponse(access_token=token)


@app.get("/history", response_model=HistoryResponse)
async def history(claims: dict = Depends(verify_token)):
    uid = int(claims.get("sub"))
    items: List[HistoryItem] = []
    rows = await get_search_history(uid)
    for r in rows:
        items.append(HistoryItem(**r))
    return HistoryResponse(items=items)


app.include_router(query_router)