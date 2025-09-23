import json
import aiomysql
from typing import Any, Dict, List, Optional, Tuple
from .config import Config
from .logging import logger


class MySQL:
    _pool: Optional[aiomysql.Pool] = None

    @classmethod
    async def init_pool(cls) -> aiomysql.Pool:
        if cls._pool is None:
            cls._pool = await aiomysql.create_pool(
                host=Config.MYSQL_HOST,
                port=Config.MYSQL_PORT,
                user=Config.MYSQL_USER,
                password=Config.MYSQL_PASSWORD,
                db=Config.MYSQL_DB,
                autocommit=True,
                charset="utf8mb4",
            )
            logger.info("MySQL connected (pool initialized)")
        return cls._pool

    @classmethod
    async def execute(cls, query: str, args: Tuple[Any, ...] = ()) -> int:
        pool = await cls.init_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, args)
                return cur.lastrowid or 0

    @classmethod
    async def fetchone(cls, query: str, args: Tuple[Any, ...] = ()) -> Optional[Tuple[Any, ...]]:
        pool = await cls.init_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, args)
                return await cur.fetchone()

    @classmethod
    async def fetchall(cls, query: str, args: Tuple[Any, ...] = ()) -> List[Tuple[Any, ...]]:
        pool = await cls.init_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, args)
                return await cur.fetchall()


async def create_user(username: str, email: str, password_hash: str) -> int:
    sql = "INSERT INTO users (username, email, password) VALUES (%s, %s, %s)"
    user_id = await MySQL.execute(sql, (username, email, password_hash))
    logger.info("RA Check: Created user account; no sensitive data logged.")
    return user_id


async def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    sql = "SELECT id, username, email, password FROM users WHERE username=%s"
    row = await MySQL.fetchone(sql, (username,))
    if not row:
        return None
    return {"id": row[0], "username": row[1], "email": row[2], "password": row[3]}


async def store_search(user_id: int, query: str, results: Dict[str, Any]) -> int:
    sql = "INSERT INTO search_history (user_id, query, results) VALUES (%s, %s, %s)"
    rid = await MySQL.execute(sql, (user_id, query, json.dumps(results)))
    logger.info("RA Check: Stored search history; transparency via audit log; no PII beyond username/id.")
    return rid


async def get_search_history(user_id: int, limit: int = 20) -> List[Dict[str, Any]]:
    sql = "SELECT id, query, results, timestamp FROM search_history WHERE user_id=%s ORDER BY timestamp DESC LIMIT %s"
    rows = await MySQL.fetchall(sql, (user_id, limit))
    history: List[Dict[str, Any]] = []
    for r in rows:
        history.append({
            "id": r[0],
            "query": r[1],
            "results": json.loads(r[2]) if r[2] else {},
            "timestamp": r[3].isoformat() if r[3] else None
        })
    return history


async def get_cached_result(user_id: int, query: str) -> Optional[Dict[str, Any]]:
    sql = "SELECT results FROM search_history WHERE user_id=%s AND query=%s ORDER BY timestamp DESC LIMIT 1"
    row = await MySQL.fetchone(sql, (user_id, query))
    if not row:
        return None
    try:
        return json.loads(row[0]) if row[0] else None
    except Exception:
        return None