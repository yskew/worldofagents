import secrets

import bcrypt


def generate_agent_key() -> str:
    return secrets.token_urlsafe(48)


def hash_agent_key(key: str) -> tuple[str, str]:
    salt = bcrypt.gensalt()
    key_hash = bcrypt.hashpw(key.encode(), salt)
    return key_hash.decode(), salt.decode()


def verify_agent_key(key: str, key_hash: str) -> bool:
    return bcrypt.checkpw(key.encode(), key_hash.encode())
