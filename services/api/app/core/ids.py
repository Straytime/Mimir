from hashlib import sha256
import secrets


def generate_id(prefix: str) -> str:
    return f"{prefix}_{secrets.token_hex(12)}"


def hash_secret(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()
