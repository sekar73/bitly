import os
import json
import math
import re
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from urllib.parse import urlsplit

import psycopg
from psycopg_pool import ConnectionPool
from psycopg.rows import dict_row
import redis
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, field_validator

pool = ConnectionPool(os.environ['DATABASE_URL'], open=False, kwargs={'row_factory': dict_row})
cache = redis.Redis.from_url(os.environ.get('REDIS_URL', 'redis://redis:6379/0'), socket_connect_timeout=1, socket_timeout=1, decode_responses=True)
from app.auth import token_subject, unauthorized

@asynccontextmanager
async def lifespan(app):
    pool.open(wait=True)
    if os.environ.get('SERVICE_ROLE') == 'write':
        with pool.connection() as conn:
            conn.execute('''CREATE TABLE IF NOT EXISTS users (
                id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                email TEXT NOT NULL UNIQUE, password_hash TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(), is_active BOOLEAN NOT NULL DEFAULT true)''')
            conn.execute('CREATE SEQUENCE IF NOT EXISTS url_counter START 100000')
            conn.execute('''CREATE TABLE IF NOT EXISTS urls (
                code TEXT PRIMARY KEY, original_url TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(), expires_at TIMESTAMPTZ)''')
            # Existing links remain public but unowned; never assign them to a new registrant.
            conn.execute('ALTER TABLE urls ADD COLUMN IF NOT EXISTS created_by BIGINT REFERENCES users(id)')
            conn.execute('CREATE INDEX IF NOT EXISTS urls_owner_created_idx ON urls(created_by, created_at DESC, code)')
    yield
    pool.close()

class Link(BaseModel):
    original_url: str
    alias: str | None = None
    expires_at: datetime | None = None

    @field_validator('original_url')
    @classmethod
    def valid_url(cls, value):
        parts = urlsplit(value)
        if len(value) > 4096 or parts.scheme not in ('http', 'https') or not parts.hostname or parts.username or any(ord(c) < 33 for c in value):
            raise ValueError('Use a valid HTTP or HTTPS URL without credentials or whitespace')
        return value

    @field_validator('alias')
    @classmethod
    def valid_alias(cls, value):
        if value is not None and (not re.fullmatch(r'[a-zA-Z0-9_-]{3,32}', value) or value in {'api', 'static', 'health', 'docs', 'redoc', 'openapi.json'}):
            raise ValueError('Alias must contain 3–32 letters, digits, underscores or hyphens and cannot be reserved')
        return value

    @field_validator('expires_at')
    @classmethod
    def valid_expiry(cls, value):
        if value is not None and (value.tzinfo is None or value <= datetime.now(timezone.utc)):
            raise ValueError('Expiration must be in the future with a timezone')
        return value

def current_user(user_id: int = Depends(token_subject)):
    with pool.connection() as conn:
        user = conn.execute('SELECT id, email FROM users WHERE id=%s AND is_active', (user_id,)).fetchone()
    if not user:
        raise unauthorized()
    return user

def base62(number):
    alphabet = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
    result = ''
    while number:
        number, rem = divmod(number, 62)
        result = alphabet[rem] + result
    return result or '0'

def serialize(row):
    row = {k: v for k, v in row.items() if k != 'created_by'}
    return {**row, 'short_path': '/s/' + row['code']}

def health():
    with pool.connection() as conn:
        conn.execute('SELECT 1')
    try:
        cache.ping()
        cache_status = 'up'
    except redis.RedisError:
        cache_status = 'unavailable; database fallback active'
    return {'service': os.environ['SERVICE_ROLE'], 'database': 'up', 'cache': cache_status}

def invalidate(code):
    try:
        cache.delete('bitly:link:' + code)
    except redis.RedisError:
        pass

