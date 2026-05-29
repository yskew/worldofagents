from app.utils.crypto import generate_agent_key, hash_agent_key, verify_agent_key


def create_agent_credentials() -> tuple[str, str, str]:
    plain_key = generate_agent_key()
    key_hash, key_salt = hash_agent_key(plain_key)
    return plain_key, key_hash, key_salt


def verify_agent_credentials(plain_key: str, key_hash: str) -> bool:
    return verify_agent_key(plain_key, key_hash)
