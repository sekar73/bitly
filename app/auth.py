"""Password hashing and short-lived, signed access tokens."""
import os
import secrets
from datetime import datetime, timedelta, timezone
from threading import BoundedSemaphore

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field, field_validator

JWT_SECRET = os.environ['JWT_SECRET']
if len(JWT_SECRET.encode()) < 32:
    raise RuntimeError('JWT_SECRET must contain at least 32 bytes')
JWT_TTL = int(os.environ.get('JWT_TTL_MINUTES', '30'))
if not 1 <= JWT_TTL <= 1440:
    raise RuntimeError('JWT_TTL_MINUTES must be between 1 and 1440')
ISSUER = 'bitly-lab'
AUDIENCE = 'bitly-api'
# Serialize expensive password work to stay within this lab's 256 MiB app limit.
hasher = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=1)
password_slot = BoundedSemaphore(1)
dummy_hash = hasher.hash(secrets.token_urlsafe(32))
bearer = HTTPBearer(auto_error=False)

class Credentials(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=12, max_length=128)

    @field_validator('email')
    @classmethod
    def normalize_email(cls, value):
        import re
        value = value.strip().lower()
        if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', value):
            raise ValueError('Enter a valid email address')
        return value

def hash_password(password):
    with password_slot:
        return hasher.hash(password)

def verify_password(password, stored_hash):
    with password_slot:
        try:
            return hasher.verify(stored_hash or dummy_hash, password)
        except (VerificationError, InvalidHashError):
            return False

def issue_token(user):
    now = datetime.now(timezone.utc)
    token = jwt.encode({'sub': str(user['id']), 'iat': now, 'exp': now + timedelta(minutes=JWT_TTL),
                        'iss': ISSUER, 'aud': AUDIENCE}, JWT_SECRET, algorithm='HS256')
    return {'access_token': token, 'token_type': 'bearer', 'expires_in': JWT_TTL * 60,
            'user': {'id': user['id'], 'email': user['email']}}

def unauthorized():
    return HTTPException(401, 'Sign in required or access token invalid/expired', headers={'WWW-Authenticate': 'Bearer'})

def token_subject(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)):
    if credentials is None:
        raise unauthorized()
    try:
        claims = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=['HS256'], issuer=ISSUER,
                            audience=AUDIENCE, options={'require': ['sub', 'iat', 'exp', 'iss', 'aud']})
        user_id = int(claims['sub'])
        if not 0 < user_id <= 2**63 - 1:
            raise ValueError('Invalid subject')
        return user_id
    except (jwt.InvalidTokenError, ValueError, TypeError):
        raise unauthorized()
