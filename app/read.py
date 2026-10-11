"""Read service: URL listing, lookup and cached public redirects."""
import os
os.environ.setdefault('SERVICE_ROLE', 'read')
import json
import math
from datetime import datetime, timezone
import redis
from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import RedirectResponse
from app.common import pool, cache, lifespan, current_user, serialize, health

app = FastAPI(title='Bitly Read Service', lifespan=lifespan, docs_url='/read/docs', openapi_url='/read/openapi.json', redoc_url=None)
app.get('/health')(health)

@app.get('/api/links')
def list_links(user: dict = Depends(current_user), offset: int = 0):
    if offset < 0:
        raise HTTPException(422, 'Offset must be positive')
    with pool.connection() as conn:
        return [serialize(row) for row in conn.execute('SELECT * FROM urls WHERE created_by=%s ORDER BY created_at DESC, code LIMIT 100 OFFSET %s', (user['id'], offset))]

@app.get('/api/links/{code}')
def retrieve_link(code: str):
    with pool.connection() as conn:
        row = conn.execute('SELECT * FROM urls WHERE code=%s', (code,)).fetchone()
    if not row:
        raise HTTPException(404, 'Link not found')
    if row['expires_at'] and row['expires_at'] <= datetime.now(timezone.utc):
        raise HTTPException(410, 'Link expired')
    return serialize(row)

@app.get('/s/{code}')
def redirect(code: str):
    # Cache-aside: bounded staleness (30s) on concurrent mutations or Redis failure.
    key = 'bitly:link:' + code
    try:
        cached = cache.get(key)
        if cached:
            row = json.loads(cached)
            expiry = datetime.fromisoformat(row['expires_at']) if row['expires_at'] else None
            if expiry and expiry <= datetime.now(timezone.utc):
                raise HTTPException(410, 'Link expired')
            return RedirectResponse(row['original_url'], status_code=302, headers={'Cache-Control': 'no-store'})
    except (redis.RedisError, ValueError, KeyError):
        pass
    row = retrieve_link(code)
    ttl = 30
    if row['expires_at']:
        ttl = min(ttl, math.floor((row['expires_at'] - datetime.now(timezone.utc)).total_seconds()))
    if ttl > 0:
        try:
            cache.setex(key, ttl, json.dumps({'original_url': row['original_url'], 'expires_at': row['expires_at'].isoformat() if row['expires_at'] else None}))
        except redis.RedisError:
            pass
    return RedirectResponse(row['original_url'], status_code=302, headers={'Cache-Control': 'no-store'})
