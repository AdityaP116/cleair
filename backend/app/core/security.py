import secrets
import hashlib
import hmac
from typing import Tuple

def generate_sensor_key() -> Tuple[str, str, str]:
    """
    Generates a high-entropy 256-bit cryptographically secure token.
    Returns:
      (plaintext_key, key_prefix, key_hash)
    Plaintext key is formatted as: sq_live_<prefix>_<secret>
    """
    secret = secrets.token_urlsafe(32) # 256-bit entropy
    prefix = secrets.token_hex(4)      # 8 chars prefix for identification
    full_key = f"sq_live_{prefix}_{secret}"
    
    salt = secrets.token_hex(16)
    key_hash = hash_sensor_key(full_key, salt)
    return full_key, prefix, salt, key_hash

def hash_sensor_key(key: str, salt: str) -> str:
    """Computes salted SHA-256 hash."""
    return hashlib.sha256((salt + key).encode("utf-8")).hexdigest()

def verify_sensor_key(provided_key: str, salt: str, expected_hash: str) -> bool:
    """Verifies provided key against expected hash using constant-time comparison."""
    computed_hash = hash_sensor_key(provided_key, salt)
    return hmac.compare_digest(computed_hash, expected_hash)
