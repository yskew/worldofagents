from app.utils.crypto import generate_agent_key, hash_agent_key, verify_agent_key


def test_generate_key_length_and_format():
    key = generate_agent_key()
    assert len(key) >= 40
    assert all(c.isalnum() or c in "-_" for c in key)


def test_hash_and_verify():
    key = generate_agent_key()
    key_hash, key_salt = hash_agent_key(key)
    assert verify_agent_key(key, key_hash) is True


def test_verify_wrong_key():
    key = generate_agent_key()
    key_hash, _ = hash_agent_key(key)
    assert verify_agent_key("wrong-key-entirely", key_hash) is False


def test_different_keys_different_hashes():
    k1 = generate_agent_key()
    k2 = generate_agent_key()
    h1, _ = hash_agent_key(k1)
    h2, _ = hash_agent_key(k2)
    assert h1 != h2
