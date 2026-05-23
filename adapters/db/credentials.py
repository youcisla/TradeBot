"""Option B credential store — Argon2id-derived key + AES-256-GCM at rest.

Threat model
─────────────
• DB dump leaked alone                                    → ✅ encrypted (requires dashboard password)
• Bot machine stolen (powered off)                       → ✅ same as above
• Bot machine compromised at runtime (root/cold-boot)     → ❌ plaintext is in memory; no defence possible
• User forgets dashboard password                        → ⚠  MT5 credentials become unrecoverable; re-enter required

Design flow
───────────
1. User logs into dashboard with email + dashboard password
2. Dashboard password → bcrypt hash for session auth
   → ALSO derive an encryption key via Argon2id (Argon2id(password, salt, ops, mem))
   → derived key NEVER stored on disk — recomputed on each login
3. First-time setup: user enters MT5 account/password/server in UI
4. Encrypted with derived key, stored in `broker_accounts`:
   - id, user_id, account_number, server         (plaintext — non-sensitive identifiers)
   - encrypted_password  (nonce‖ciphertext‖tag, base64)
   - salt                (per-profile Argon2id salt)
   - profile_label       (user-chosen: "Demo", "Live", "Test")
   - is_active           (which profile the bot is currently using)
   - kdf_params          (Argon2id tuning for future re-keying)
5. On bot startup:
   - Bot reads broker_accounts where is_active=TRUE
   - Bot CANNOT decrypt without user's dashboard password
   - Bot enters WAITING_FOR_AUTH state, exposes /api/auth/unlock
   - User opens dashboard → dashboard sends derived key over HTTPS
   - Bot decrypts MT5 password in memory ONLY, calls mt5.login()
   - Decrypted password held in memory for session, never written to disk
6. On profile switch:
   - User selects different profile in UI
   - Dashboard POSTs to /api/auth/switch-profile with new profile id + dashboard pw
   - Bot disconnects current MT5 session, decrypts new credentials, mt5.login()
   - Old in-memory password zeroed (best-effort in Python)

Module-level rules
──────────────────
• BrokerCredentials.password is NEVER logged, stored, or pickled
• derive_key() always returns a fresh bytes object — caller owns the memory
• All methods log at DEBUG level only; no credential details in INFO/WARNING
"""

from __future__ import annotations

import base64
import json
import logging
import secrets
from dataclasses import dataclass
from typing import TYPE_CHECKING

from argon2.exceptions import VerifyMismatchError

if TYPE_CHECKING:
    from adapters.db.pool import ConnectionPool

logger = logging.getLogger(__name__)

# ── Defaults (RFC 9106 low-memory profile — ~50ms per derive on modern hardware) ──

_DEFAULT_KDF_OPS_LIMIT = 3             # argon2id time cost (RFC 9106)
_DEFAULT_KDF_MEM_LIMIT = 65536           # kibibytes (64 MiB — RFC 9106 LOW_MEMORY)
_DEFAULT_KDF_PARALLELISM = 4             # parallel threads (RFC 9106)


# ── Crypto protocol dataclass ──────────────────────────────────────────────────

@dataclass(frozen=True)
class CryptoProtocol:
    """Argon2id parameters used for key derivation.

    Stored alongside each credential so future re-keying is possible
    without data loss.
    """

    ops_limit: int = _DEFAULT_KDF_OPS_LIMIT
    mem_limit_kib: int = _DEFAULT_KDF_MEM_LIMIT
    parallelism: int = _DEFAULT_KDF_PARALLELISM

    def to_json(self) -> str:
        return json.dumps({
            "ops_limit": self.ops_limit,
            "mem_limit_kib": self.mem_limit_kib,
            "parallelism": self.parallelism,
        })

    @classmethod
    def from_json(cls, raw: str | None) -> "CryptoProtocol":
        if not raw:
            return cls()
        try:
            d = json.loads(raw)
            return cls(
                ops_limit=d.get("ops_limit", _DEFAULT_KDF_OPS_LIMIT),
                mem_limit_kib=d.get("mem_limit_kib", _DEFAULT_KDF_MEM_LIMIT),
                parallelism=d.get("parallelism", _DEFAULT_KDF_PARALLELISM),
            )
        except (json.JSONDecodeError, TypeError):
            return cls()

    @classmethod
    def current(cls) -> "cls":
        """Returns the protocol matching the current library defaults."""
        return cls()


# ── Broker credentials (in-memory only) ─────────────────────────────────────

@dataclass(frozen=True)
class BrokerCredentials:
    """Plaintext broker credentials — in-memory only, never persisted."""

    account: str
    server: str
    password: str  # plaintext — caller must not log or retain after use


# ── Profile summary (for UI — no secrets) ─────────────────────────────────────

@dataclass(frozen=True)
class ProfileSummary:
    id: int
    user_id: int | None
    profile_label: str
    account_number: str
    server: str
    is_demo: bool
    is_active: bool


# ── Credential store ────────────────────────────────────────────────────────────

class CredentialStore:
    """Manages encrypted broker credentials in the broker_accounts table.

    Callers
    ───────
    • api/routes/auth.py  — login, profile CRUD, switch
    • orchestration/lifecycle.py — bot startup unlock sequence
    """

    def __init__(self, pool: "ConnectionPool") -> None:
        self._pool = pool

    # ── private helpers ──────────────────────────────────────────────────────

    def _conn(self):
        return self._pool.get_conn()

    def _put(self, conn) -> None:
        self._pool.put_conn(conn)

    # ── key derivation ───────────────────────────────────────────────────────

    def derive_key(self, dashboard_password: str, salt: bytes) -> bytes:
        """Argon2id KDF — derive a 32-byte encryption key from the dashboard password.

        Parameters
        ----------
        dashboard_password : str
            The user's dashboard password (same one used for session auth).
        salt : bytes
            Per-profile random salt (16 bytes minimum; generated when the profile
            is first stored via ``secrets.token_bytes(16)``).

        Returns
        -------
        bytes
            32-byte AES-256 key. Caller owns this buffer.

        Note
        ----
        The derived key is NEVER stored anywhere. It must be recomputed from the
        password on each dashboard login session.
        """
        from argon2.low_level import hash_secret, Type

        result = hash_secret(
            secret=dashboard_password.encode("utf-8"),
            salt=salt,
            time_cost=_DEFAULT_KDF_OPS_LIMIT,
            memory_cost=_DEFAULT_KDF_MEM_LIMIT,
            parallelism=_DEFAULT_KDF_PARALLELISM,
            hash_len=32,      # 256 bits → AES-256 key
            type=Type.ID,    # Argon2id = 2
        )
        # hash_secret returns a PHC-formatted byte string:
        # $argon2id$v=19$m=65536,t=3,p=4$<salt_b64>.<hash_b64>
        # The AES key is the 32-byte raw hash, base64-encoded as the last segment.
        s = result.decode("ascii")
        # salt (22 base64 chars) is followed by a '$' separator, then hash (43 chars)
        salt_end = s.rfind("$") - 1  # back up over the '$' before the hash segment
        hash_segment = s[salt_end + 1:]  # +1 skips the '$'
        # hash_segment is 43 chars of base64 — pad to multiple of 4 for std_b64 decode
        key = base64.b64decode(hash_segment + "==")
        return key

    # ── encrypt / decrypt ──────────────────────────────────────────────────

    @staticmethod
    def encrypt(plaintext: str, key: bytes) -> str:
        """AES-256-GCM encryption — returns base64(nonce‖ciphertext‖tag).

        Parameters
        ----------
        plaintext : str
            The broker password to encrypt.
        key : bytes
            32-byte key from derive_key().

        Returns
        -------
        str
            base64-encoded ciphertext suitable for storage in a TEXT column.
        """
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        nonce = secrets.token_bytes(12)           # 96-bit nonce for GCM
        aesgcm = AESGCM(key)
        ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
        # nonce (12) || ciphertext || tag (16) — AESGCM appends tag automatically
        return base64.b64encode(nonce + ciphertext).decode("ascii")

    @staticmethod
    def decrypt(encoded: str, key: bytes) -> str:
        """AES-256-GCM decryption.

        Parameters
        ----------
        encoded : str
            base64(nonce‖ciphertext‖tag) from encrypt().
        key : bytes
            The same 32-byte key used for encryption.

        Returns
        -------
        str
            The original plaintext broker password.

        Raises
        ------
        cryptography.exceptions.InvalidTag
            If the ciphertext has been tampered with or the key is wrong.
        """
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        data = base64.b64decode(encoded)
        nonce = data[:12]
        ciphertext = data[12:]
        aesgcm = AESGCM(key)
        return aesgcm.decrypt(nonce, ciphertext, None).decode("utf-8")

    # ── store ─────────────────────────────────────────────────────────────────

    def store(
        self,
        *,
        user_id: int | None,
        profile_label: str,
        account_number: str,
        server: str,
        password: str,
        derived_key: bytes,
    ) -> int:
        """Encrypt and persist a new broker credential profile.

        Parameters
        ----------
        user_id : int | None
            Dashboard user who owns this profile.
        profile_label : str
            User-chosen name ("Demo", "Live", "Test").
        account_number : str
            MT5 account number (stored plaintext).
        server : str
            MT5 server name (stored plaintext).
        password : str
            The plaintext MT5 trading password to encrypt and store.
        derived_key : bytes
            32-byte key from derive_key().

        Returns
        -------
        int
            The PostgreSQL id of the newly inserted row.
        """
        salt = secrets.token_bytes(16)
        encrypted = self.encrypt(password, derived_key)
        protocol = CryptoProtocol.current()

        conn = self._conn()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO broker_accounts
                            (user_id, profile_label, account_number,
                             encrypted_password, salt, server,
                             kdf_ops_limit, kdf_mem_limit_kib, kdf_parallelism,
                             is_demo, created_at, last_connected)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, TRUE, NOW(), NULL)
                        RETURNING id
                        """,
                        (
                            user_id,
                            profile_label,
                            account_number,
                            encrypted,
                            salt,
                            server,
                            protocol.ops_limit,
                            protocol.mem_limit_kib,
                            protocol.parallelism,
                        ),
                    )
                    return cur.fetchone()[0]
        finally:
            self._put(conn)

    # ── load ────────────────────────────────────────────────────────────────────

    def load(
        self,
        *,
        profile_id: int,
        derived_key: bytes,
        user_id: int | None = None,
    ) -> BrokerCredentials:
        """Fetch and decrypt broker credentials for the given profile.

        Parameters
        ----------
        profile_id : int
            The broker_accounts.id to load.
        derived_key : bytes
            32-byte key from derive_key().
        user_id : int | None
            If provided, verifies the profile belongs to this user.

        Returns
        -------
        BrokerCredentials
            Plaintext account, server, password — caller must NOT persist or log.

        Raises
        ------
        LookupError
            If the profile does not exist or belongs to a different user.
        cryptography.exceptions.InvalidTag
            If decryption fails (wrong key or tampered ciphertext).
        """
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                if user_id is not None:
                    cur.execute(
                        """SELECT id, user_id, account_number, encrypted_password,
                                  salt, server, kdf_ops_limit, kdf_mem_limit_kib,
                                  kdf_parallelism, profile_label
                           FROM broker_accounts
                           WHERE id = %s AND user_id = %s""",
                        (profile_id, user_id),
                    )
                else:
                    cur.execute(
                        """SELECT id, user_id, account_number, encrypted_password,
                                  salt, server, kdf_ops_limit, kdf_mem_limit_kib,
                                  kdf_parallelism, profile_label
                           FROM broker_accounts
                           WHERE id = %s""",
                        (profile_id,),
                    )
                row = cur.fetchone()
                if row is None:
                    raise LookupError(f"No broker account with id={profile_id}")

                (
                    row_id,
                    row_uid,
                    account_number,
                    encrypted_password,
                    salt,
                    server,
                    kdf_ops,
                    kdf_mem,
                    kdf_par,
                    profile_label,
                ) = row

                protocol = CryptoProtocol(
                    ops_limit=kdf_ops or _DEFAULT_KDF_OPS_LIMIT,
                    mem_limit_kib=kdf_mem or _DEFAULT_KDF_MEM_LIMIT,
                    parallelism=kdf_par or _DEFAULT_KDF_PARALLELISM,
                )
                plaintext = self.decrypt(encrypted_password, derived_key)
                return BrokerCredentials(
                    account=account_number,
                    server=server,
                    password=plaintext,
                )
        finally:
            self._put(conn)

    # ── list profiles ───────────────────────────────────────────────────────

    def list_profiles(self, user_id: int | None = None) -> list[ProfileSummary]:
        """List all profiles for a user — NEVER returns passwords.

        Parameters
        ----------
        user_id : int | None
            If provided, returns only profiles for this user. If None,
            returns all profiles (used by admin endpoints).

        Returns
        -------
        list[ProfileSummary]
            Lightweight objects safe for API responses.
        """
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                if user_id is not None:
                    cur.execute(
                        """SELECT id, user_id, profile_label, account_number,
                                  server, is_demo, is_active
                           FROM broker_accounts
                           WHERE user_id = %s
                           ORDER BY created_at DESC""",
                        (user_id,),
                    )
                else:
                    cur.execute(
                        """SELECT id, user_id, profile_label, account_number,
                                  server, is_demo, is_active
                           FROM broker_accounts
                           ORDER BY created_at DESC"""
                    )
                return [
                    ProfileSummary(
                        id=r[0],
                        user_id=r[1],
                        profile_label=r[2] or "",
                        account_number=r[3],
                        server=r[4],
                        is_demo=r[5],
                        is_active=r[6],
                    )
                    for r in cur.fetchall()
                ]
        finally:
            self._put(conn)

    # ── set active ─────────────────────────────────────────────────────────

    def set_active(self, profile_id: int, user_id: int | None = None) -> None:
        """Mark a profile as the active broker account.

        Deactivates all other profiles for the same user first.
        """
        conn = self._conn()
        try:
            with conn:
                with conn.cursor() as cur:
                    if user_id is not None:
                        cur.execute(
                            "UPDATE broker_accounts SET is_active = FALSE WHERE user_id = %s",
                            (user_id,),
                        )
                        cur.execute(
                            """UPDATE broker_accounts
                               SET is_active = TRUE
                               WHERE id = %s AND user_id = %s""",
                            (profile_id, user_id),
                        )
                    else:
                        cur.execute(
                            "UPDATE broker_accounts SET is_active = FALSE"
                        )
                        cur.execute(
                            "UPDATE broker_accounts SET is_active = TRUE WHERE id = %s",
                            (profile_id,),
                        )
        finally:
            self._put(conn)

    # ── delete ─────────────────────────────────────────────────────────────

    def delete(self, profile_id: int, user_id: int | None = None) -> None:
        """Delete a credential profile."""
        conn = self._conn()
        try:
            with conn:
                with conn.cursor() as cur:
                    if user_id is not None:
                        cur.execute(
                            "DELETE FROM broker_accounts WHERE id = %s AND user_id = %s",
                            (profile_id, user_id),
                        )
                    else:
                        cur.execute(
                            "DELETE FROM broker_accounts WHERE id = %s",
                            (profile_id,),
                        )
        finally:
            self._put(conn)

    # ── session tracking ─────────────────────────────────────────────────────

    def update_last_connected(self, profile_id: int) -> None:
        """Update last_connected timestamp after successful MT5 login."""
        conn = self._conn()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """UPDATE broker_accounts
                           SET last_connected = NOW()
                           WHERE id = %s""",
                        (profile_id,),
                    )
        finally:
            self._put(conn)
