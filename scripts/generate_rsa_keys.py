#!/usr/bin/env python3
"""Generate RSA keypair for AgentVerify JWT signing. Copy output to .env."""
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

private_pem = private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption(),
).decode()

public_pem = private_key.public_key().public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo,
).decode()

print("=== RSA_PRIVATE_KEY_PEM ===")
print(private_pem)
print("=== RSA_PUBLIC_KEY_PEM ===")
print(public_pem)
