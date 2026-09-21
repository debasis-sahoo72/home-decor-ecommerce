import hashlib
import hmac
import secrets
import time

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

hasher = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=2)
DUMMY_HASH = hasher.hash(secrets.token_urlsafe(32))


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def verify_password(stored: str, password: str) -> bool:
    try:
        return hasher.verify(stored, password)
    except (VerificationError, InvalidHashError):
        return False


def preauth_token(secret: str) -> str:
    value = f"{int(time.time())}.{secrets.token_urlsafe(32)}"
    signature = hmac.new(secret.encode(), value.encode(), hashlib.sha256).hexdigest()
    return f"{value}.{signature}"


def valid_preauth(token: str, secret: str, max_age: int = 600) -> bool:
    try:
        stamp, random, signature = token.split(".")
        age = time.time() - int(stamp)
        expected = hmac.new(
            secret.encode(), f"{stamp}.{random}".encode(), hashlib.sha256
        ).hexdigest()
        return 0 <= age <= max_age and hmac.compare_digest(signature, expected)
    except (ValueError, TypeError):
        return False
