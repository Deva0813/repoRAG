from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

# Generate RSA private key
key = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048,
)


# Serialize private key
private_pem = key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption(),
)


# Serialize public key
public_pem = key.public_key().public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo,
)


# Create output directory
output_dir = Path("keys")
output_dir.mkdir(parents=True, exist_ok=True)


# Write keys to files
private_key_path = output_dir / "jwt_private_key.pem"
public_key_path = output_dir / "jwt_public_key.pem"

private_key_path.write_bytes(private_pem)
public_key_path.write_bytes(public_pem)


print(f"Private key: {private_key_path}")
print(f"Public key:  {public_key_path}")
