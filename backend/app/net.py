"""TLS setup: verify HTTPS with the operating system's certificate store.

Why: antivirus "HTTPS scanning" (e.g. Kaspersky) and some college/office
proxies re-sign traffic with their own root certificate. Windows/macOS trust
that root, but Python's bundled list (certifi) does not, so every API call
fails with CERTIFICATE_VERIFY_FAILED. `truststore` makes Python use the OS
store instead. Certificate verification stays fully ON.
"""

from __future__ import annotations

import logging

log = logging.getLogger("litlens.net")
_done = False


def use_system_trust_store() -> None:
    """Idempotent. Call once at startup, before any HTTP client is created."""
    global _done
    if _done:
        return
    try:
        import truststore

        truststore.inject_into_ssl()
    except Exception as e:  # never block startup; fall back to certifi
        log.warning("Could not enable OS certificate store: %s", type(e).__name__)
    _done = True
