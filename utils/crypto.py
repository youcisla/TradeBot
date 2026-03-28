"""Symmetric encryption for sensitive data stored in the database.

Uses AES-256-CBC + HMAC-SHA256.  The encryption key is derived from
``ENCRYPTION_KEY`` in .env via SHA-256.

Format: base64( IV(16) + HMAC(32) + ciphertext )

Both the Python bot and the Node.js web app use the same format so
either side can encrypt/decrypt broker passwords.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import os

try:
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.primitives import padding as _padding
except ImportError as _err:
    raise ImportError(
        "The 'cryptography' package is required for broker password encryption. "
        "Install it with: pip install cryptography>=42.0"
    ) from _err

from config import settings

logger = logging.getLogger(__name__)

_key: bytes | None = None


def _get_key() -> bytes | None:
    """Derive a 32-byte AES key from the ENCRYPTION_KEY env var."""
    global _key
    if _key is not None:
        return _key

    raw = getattr(settings, "ENCRYPTION_KEY", "")
    if not raw:
        logger.warning(
            "ENCRYPTION_KEY not set — broker passwords will be stored in plaintext!"
        )
        return None

    _key = hashlib.sha256(raw.encode()).digest()
    return _key


def encrypt(plaintext: str) -> str:
    """Encrypt a string.  Returns base64(iv + hmac + ciphertext).

    If no encryption key is configured, returns plaintext unchanged.
    """
    key = _get_key()
    if key is None:
        return plaintext

    iv = os.urandom(16)
    padder = _padding.PKCS7(128).padder()
    padded = padder.update(plaintext.encode()) + padder.finalize()

    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(padded) + encryptor.finalize()

    mac = hmac.new(key, iv + ciphertext, hashlib.sha256).digest()
    return base64.b64encode(iv + mac + ciphertext).decode()


def decrypt(ciphertext: str) -> str:
    """Decrypt a string previously encrypted with ``encrypt()``.

    If no encryption key is configured or decryption fails (legacy
    plaintext), returns the input unchanged.
    """
    key = _get_key()
    if key is None:
        return ciphertext

    try:
        raw = base64.b64decode(ciphertext)
    except Exception:
        return ciphertext  # not base64 → legacy plaintext

    if len(raw) < 48:
        return ciphertext  # too short → plaintext

    iv = raw[:16]
    stored_mac = raw[16:48]
    encrypted = raw[48:]

    # Verify HMAC
    computed_mac = hmac.new(key, iv + encrypted, hashlib.sha256).digest()
    if not hmac.compare_digest(stored_mac, computed_mac):
        return ciphertext  # HMAC mismatch → legacy plaintext

    try:
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
        decryptor = cipher.decryptor()
        padded = decryptor.update(encrypted) + decryptor.finalize()
        unpadder = _padding.PKCS7(128).unpadder()
        plaintext = unpadder.update(padded) + unpadder.finalize()
        return plaintext.decode()
    except Exception:
        logger.debug("Decryption failed — returning raw value (legacy data?)")
        return ciphertext
