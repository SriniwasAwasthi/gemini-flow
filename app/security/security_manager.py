"""
Production-Grade Security & Privacy Manager for Gemini Flow.
Provides Windows DPAPI / secure credential storage, logging sanitization,
history retention enforcement, and data privacy controls.
"""
import os
import re
import base64
import ctypes
import logging
from ctypes import wintypes
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger("GeminiFlow.Security")


class DATA_BLOB(ctypes.Structure):
    _fields_ = [
        ("cbData", wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_byte))
    ]


class SensitiveDataFilter(logging.Filter):
    """
    Sanitizes log messages so sensitive API keys, authorization tokens,
    or credentials are never written to log files in plain text.
    """
    KEY_PATTERN = re.compile(r'(key=|[Aa][Pp][Ii][_-]?[Kk][Ee][Yy]["\':\s=]+|Bearer\s+)([A-Za-z0-9_\-\.]{15,})')

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = self.KEY_PATTERN.sub(r'\1[REDACTED_SECRET]', record.msg)
        return True


class SecurityManager:
    """
    Handles secure credential persistence, environment-variable fallback,
    log redaction, data retention, and privacy controls.
    """
    def __init__(self, app_dir: Optional[Path] = None):
        self.app_dir = app_dir or (Path(os.environ.get("APPDATA", Path.home())) / "GeminiFlow")
        self.app_dir.mkdir(parents=True, exist_ok=True)
        self.cred_file = self.app_dir / ".credentials.bin"
        self._setup_log_sanitization()

    def _setup_log_sanitization(self):
        """Attaches sensitive data filter to root and app loggers."""
        root_logger = logging.getLogger()
        sanitizer = SensitiveDataFilter()
        root_logger.addFilter(sanitizer)
        for handler in root_logger.handlers:
            handler.addFilter(sanitizer)

    # ---------------------------------------------------------
    # Windows DPAPI Secret Encryption / Decryption
    # ---------------------------------------------------------
    @staticmethod
    def _encrypt_dpapi(plaintext: str) -> Optional[bytes]:
        """Encrypts a string using Windows Data Protection API (CryptProtectData)."""
        if os.name != "nt":
            return None
        try:
            crypt32 = ctypes.windll.crypt32
            kernel32 = ctypes.windll.kernel32

            raw_bytes = plaintext.encode("utf-8")
            data_in = DATA_BLOB()
            data_in.cbData = len(raw_bytes)
            data_in.pbData = ctypes.cast(ctypes.create_string_buffer(raw_bytes), ctypes.POINTER(ctypes.c_byte))

            data_out = DATA_BLOB()
            # CRYPTPROTECT_UI_FORBIDDEN = 0x1
            if crypt32.CryptProtectData(ctypes.byref(data_in), "GeminiFlowSecret", None, None, None, 0x1, ctypes.byref(data_out)):
                encrypted_bytes = ctypes.string_at(data_out.pbData, data_out.cbData)
                kernel32.LocalFree(data_out.pbData)
                return encrypted_bytes
        except Exception as e:
            logger.debug(f"DPAPI encryption unavailable: {e}")
        return None

    @staticmethod
    def _decrypt_dpapi(cipher_bytes: bytes) -> Optional[str]:
        """Decrypts bytes using Windows Data Protection API (CryptUnprotectData)."""
        if os.name != "nt":
            return None
        try:
            crypt32 = ctypes.windll.crypt32
            kernel32 = ctypes.windll.kernel32

            data_in = DATA_BLOB()
            data_in.cbData = len(cipher_bytes)
            data_in.pbData = ctypes.cast(ctypes.create_string_buffer(cipher_bytes), ctypes.POINTER(ctypes.c_byte))

            data_out = DATA_BLOB()
            if crypt32.CryptUnprotectData(ctypes.byref(data_in), None, None, None, None, 0x1, ctypes.byref(data_out)):
                decrypted_bytes = ctypes.string_at(data_out.pbData, data_out.cbData)
                kernel32.LocalFree(data_out.pbData)
                return decrypted_bytes.decode("utf-8", errors="ignore")
        except Exception as e:
            logger.debug(f"DPAPI decryption unavailable: {e}")
        return None

    @classmethod
    def encrypt_secret(cls, plaintext: str) -> bytes:
        """Helper to encrypt any string using DPAPI or base64 fallback."""
        dpapi = cls._encrypt_dpapi(plaintext)
        if dpapi:
            return b"DPAPI:" + dpapi
        return b"B64:" + base64.b64encode(plaintext.encode("utf-8"))

    @classmethod
    def decrypt_secret(cls, cipher: bytes) -> str:
        """Helper to decrypt any bytes using DPAPI or base64 fallback."""
        if cipher.startswith(b"DPAPI:"):
            return cls._decrypt_dpapi(cipher[6:]) or ""
        elif cipher.startswith(b"B64:"):
            return base64.b64decode(cipher[4:]).decode("utf-8", errors="ignore")
        return ""

    @staticmethod
    def mask_api_key(api_key: str) -> str:
        return SecurityManager.mask_key(api_key)

    def save_api_key(self, api_key: str) -> bool:
        """Securely stores the Gemini API key using DPAPI or obfuscated storage."""
        cleaned = api_key.strip()
        if not cleaned:
            if self.cred_file.exists():
                try:
                    self.cred_file.unlink()
                except Exception:
                    pass
            return True

        dpapi_bytes = self._encrypt_dpapi(cleaned)
        try:
            if dpapi_bytes:
                with open(self.cred_file, "wb") as f:
                    f.write(b"DPAPI:" + dpapi_bytes)
            else:
                # Portable obfuscated fallback
                obfuscated = base64.b64encode(cleaned.encode("utf-8"))
                with open(self.cred_file, "wb") as f:
                    f.write(b"B64:" + obfuscated)
            return True
        except Exception as e:
            logger.error(f"Failed to securely persist API key: {e}")
            return False

    def load_api_key(self, fallback_key: str = "") -> str:
        """
        Loads API key prioritizing:
        1. GEMINI_API_KEY environment variable
        2. Secure encrypted credential file
        3. Passed-in configuration fallback
        """
        # 1. Environment Variable
        env_key = os.environ.get("GEMINI_API_KEY", "").strip()
        if env_key:
            return env_key

        # 2. Secure credential file
        if self.cred_file.exists():
            try:
                with open(self.cred_file, "rb") as f:
                    data = f.read()
                if data.startswith(b"DPAPI:"):
                    decrypted = self._decrypt_dpapi(data[6:])
                    if decrypted:
                        return decrypted
                elif data.startswith(b"B64:"):
                    return base64.b64decode(data[4:]).decode("utf-8", errors="ignore")
            except Exception as e:
                logger.error(f"Error reading secure credentials: {e}")

        # 3. Fallback
        return fallback_key.strip()

    @staticmethod
    def mask_key(api_key: str) -> str:
        """Returns a safe display string for the API key (e.g. 'AQ.Ab8...5QA')."""
        if not api_key:
            return "Not Configured"
        k = api_key.strip()
        if len(k) <= 8:
            return "••••••••"
        return f"{k[:6]}••••••••{k[-4:]}"

    # ---------------------------------------------------------
    # Data Retention & Privacy Governance
    # ---------------------------------------------------------
    @staticmethod
    def enforce_history_retention(history_entries: list, retention_days: int) -> tuple:
        """
        Removes unpinned history records older than retention_days.
        Pinned items (is_pinned=True) are strictly protected.
        Returns (retained_entries, purged_count).
        """
        if retention_days <= 0:
            return history_entries, 0  # 0 means unlimited

        import datetime
        now = datetime.datetime.now()
        retained = []
        purged = 0

        for entry in history_entries:
            if entry.get("is_pinned", False):
                retained.append(entry)
                continue

            ts_str = entry.get("timestamp", "")
            try:
                entry_time = datetime.datetime.fromisoformat(ts_str)
                age_days = (now - entry_time).days
                if age_days > retention_days:
                    purged += 1
                else:
                    retained.append(entry)
            except Exception:
                retained.append(entry)

        return retained, purged

    def purge_all_local_data(self) -> Dict[str, bool]:
        """One-click privacy purge of local history, logs, and performance metrics."""
        results = {}
        for fname in ["history.json", "performance_metrics.json", "gemini_flow.log", ".credentials.bin"]:
            target = self.app_dir / fname
            if target.exists():
                try:
                    target.unlink()
                    results[fname] = True
                except Exception as e:
                    logger.error(f"Failed to delete {fname}: {e}")
                    results[fname] = False
        return results
