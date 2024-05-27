from pathlib import Path

import aiofiles
from aiofiles import os
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


def generate_key_pair() -> tuple[bytes, bytes]:
    private_key: rsa.RSAPrivateKey = rsa.generate_private_key(
        public_exponent=65537, key_size=2048, backend=default_backend()
    )

    public_key: rsa.RSAPublicKey = private_key.public_key()

    private_key_pem: bytes = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )

    public_key_pem: bytes = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    return private_key_pem, public_key_pem


async def generate_and_save_key_pair(
    private_key_path: Path, public_key_path: Path
) -> tuple[bytes, bytes]:
    await os.makedirs(private_key_path.parent, exist_ok=True)
    await os.makedirs(public_key_path.parent, exist_ok=True)
    private_key_pem, public_key_pem = generate_key_pair()
    async with aiofiles.open(private_key_path, "wb") as private_key_file:
        await private_key_file.write(private_key_pem)
    async with aiofiles.open(public_key_path, "wb") as public_key_file:
        await public_key_file.write(public_key_pem)
    return private_key_pem, public_key_pem
