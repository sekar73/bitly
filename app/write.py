"""Write service: user registration/login and URL mutations."""
import os
os.environ.setdefault('SERVICE_ROLE', 'write')
import psycopg
from fastapi import FastAPI, Depends, HTTPException
from app.common import pool, lifespan, current_user, Link, base62, serialize, invalidate, health
from app.auth import Credentials, hash_password, verify_password, issue_token

app = FastAPI(title='Bitly Write Service', lifespan=lifespan, docs_url='/write/docs', openapi_url='/write/openapi.json', redoc_url=None)
app.get('/health')(health)

@app.post('/api/auth/register', status_code=201)
def register(credentials: Credentials):
    password_hash = hash_password(credentials.password)
    with pool.connection() as conn:
        user = conn.execute('INSERT INTO users(email, password_hash) VALUES (%s,%s) ON CONFLICT DO NOTHING RETURNING id, email',
                            (credentials.email, password_hash)).fetchone()
    if not user:
        raise HTTPException(409, 'Email already registered')
    return issue_token(user)

@app.post('/api/auth/login')
def login(credentials: Credentials):
    with pool.connection() as conn:
        user = conn.execute('SELECT * FROM users WHERE email=%s', (credentials.email,)).fetchone()
    valid = verify_password(credentials.password, user['password_hash'] if user else None)
    if not user or not valid or not user['is_active']:
        raise HTTPException(401, 'Invalid email or password', headers={'WWW-Authenticate': 'Bearer'})
    return issue_token(user)

@app.get('/api/auth/me')
def me(user: dict = Depends(current_user)):
    return user

@app.post('/api/links', status_code=201)
def create_link(link: Link, user: dict = Depends(current_user)):
    try:
        with pool.connection() as conn:
            # Sequence allocates unique IDs across writers; aliases may occupy those codes.
            for _ in range(20):
                code = link.alias or base62(conn.execute("SELECT nextval('url_counter') AS id").fetchone()['id'])
                row = conn.execute('''INSERT INTO urls(code, original_url, expires_at, created_by) VALUES (%s,%s,%s,%s)
                    ON CONFLICT DO NOTHING RETURNING *''', (code, link.original_url, link.expires_at, user['id'])).fetchone()
                if row:
                    return serialize(row)
                if link.alias:
                    raise HTTPException(409, 'Alias is already taken')
        raise HTTPException(503, 'Please retry')
    except psycopg.Error:
        raise HTTPException(503, 'Database unavailable')

@app.put('/api/links/{code}')
def update_link(code: str, link: Link, user: dict = Depends(current_user)):
    if link.alias is not None and link.alias != code:
        raise HTTPException(422, 'Aliases are immutable; create a new link to rename')
    with pool.connection() as conn:
        row = conn.execute('UPDATE urls SET original_url=%s, expires_at=%s WHERE code=%s AND created_by=%s RETURNING *', (link.original_url, link.expires_at, code, user['id'])).fetchone()
    if not row:
        raise HTTPException(404, 'Link not found')
    invalidate(code)
    return serialize(row)

@app.delete('/api/links/{code}', status_code=204)
def delete_link(code: str, user: dict = Depends(current_user)):
    with pool.connection() as conn:
        row = conn.execute('DELETE FROM urls WHERE code=%s AND created_by=%s RETURNING code', (code, user['id'])).fetchone()
    if not row:
        raise HTTPException(404, 'Link not found')
    invalidate(code)

