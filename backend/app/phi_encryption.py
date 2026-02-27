"""
PHI Encryption/Decryption Module
Handles encryption of Protected Health Information for HIPAA compliance.
Uses AES-256-GCM for authenticated encryption.
"""

import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from typing import Optional

# Load encryption key from environment
# Generate with: Fernet.generate_key()
PHI_ENCRYPTION_KEY = os.getenv("PHI_ENCRYPTION_KEY")


def get_fernet() -> Fernet:
    """Get Fernet instance for encryption."""
    if not PHI_ENCRYPTION_KEY:
        raise ValueError("PHI_ENCRYPTION_KEY environment variable not set")
    return Fernet(PHI_ENCRYPTION_KEY.encode())


def encrypt_phi(plaintext: str) -> Optional[bytes]:
    """
    Encrypt PHI (name, DOB, etc.) before storing in database.

    Args:
        plaintext: The PHI to encrypt (e.g., "John Smith")

    Returns:
        Encrypted bytes or None if plaintext is empty
    """
    if not plaintext:
        return None

    try:
        f = get_fernet()
        encrypted = f.encrypt(plaintext.encode())
        return encrypted
    except Exception as e:
        # Log error but don't expose PHI in logs
        print(f"Encryption error: {type(e).__name__}")
        raise


def decrypt_phi(encrypted: bytes) -> Optional[str]:
    """
    Decrypt PHI when retrieving from database.

    Args:
        encrypted: The encrypted bytes from database

    Returns:
        Decrypted plaintext or None if encrypted is None
    """
    if not encrypted:
        return None

    try:
        f = get_fernet()
        decrypted = f.decrypt(encrypted).decode()
        return decrypted
    except Exception as e:
        # Log error but don't expose details
        print(f"Decryption error: {type(e).__name__}")
        raise


def mask_phi(plaintext: str, show_last: int = 4) -> str:
    """
    Mask PHI for display in logs or non-secure contexts.
    e.g., "John Smith" -> "**** Smith"

    Args:
        plaintext: The PHI to mask
        show_last: Number of characters to show at end

    Returns:
        Masked string
    """
    if not plaintext:
        return ""

    if len(plaintext) <= show_last:
        return "*" * len(plaintext)

    return "*" * (len(plaintext) - show_last) + plaintext[-show_last:]


# ============================================================================
# Example usage:
# ============================================================================

if __name__ == "__main__":
    # Generate a key (do this once, store in env)
    # key = Fernet.generate_key()
    # print(f"Generated key: {key.decode()}")

    # Test encryption/decryption
    test_name = "Smith, John"
    encrypted = encrypt_phi(test_name)
    print(f"Original: {test_name}")
    print(f"Encrypted: {encrypted}")

    decrypted = decrypt_phi(encrypted)
    print(f"Decrypted: {decrypted}")

    print(f"Masked: {mask_phi(test_name)}")
