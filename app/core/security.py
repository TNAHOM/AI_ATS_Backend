import base64
import binascii
import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

from app.core.config import settings
from app.core.exceptions import BaseAppException

# RFC 8017 Appendix B.1: DER-encoded DigestInfo prefix for SHA-256 in RSASSA-PKCS1-v1_5.
_PKCS1_SHA256_DIGEST_INFO_PREFIX = bytes.fromhex("3031300d060960864801650304020105000420")


def _base64url_decode(segment: str) -> bytes:
    padded = segment + ("=" * (-len(segment) % 4))
    return base64.urlsafe_b64decode(padded.encode("utf-8"))


@dataclass(frozen=True)
class _RsaJwk:
    kid: str
    n: int
    e: int
    alg: str


class ClerkJWTVerifier:
    def __init__(self) -> None:
        self._jwks_cache: dict[str, _RsaJwk] = {}
        self._jwks_cached_at: float = 0.0

    def _is_cache_stale(self) -> bool:
        return (time.time() - self._jwks_cached_at) > settings.CLERK_JWKS_CACHE_TTL_SECONDS

    def _fetch_jwks(self) -> dict[str, _RsaJwk]:
        try:
            with urlopen(settings.CLERK_JWKS_URL, timeout=5) as response:
                body = response.read().decode("utf-8")
            payload = json.loads(body)
        except (URLError, TimeoutError, HTTPError, json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise BaseAppException(
                error_code="AUTH_JWKS_FETCH_FAILED",
                message="Unable to validate authentication token.",
                status_code=503,
            ) from exc

        if not isinstance(payload, dict):
            raise BaseAppException(
                error_code="AUTH_JWKS_INVALID",
                message="Unable to validate authentication token.",
                status_code=503,
            )

        keys = payload.get("keys", [])
        if not isinstance(keys, list):
            raise BaseAppException(
                error_code="AUTH_JWKS_INVALID",
                message="Unable to validate authentication token.",
                status_code=503,
            )

        parsed: dict[str, _RsaJwk] = {}
        for key in keys:
            if not isinstance(key, dict):
                continue
            if key.get("kty") != "RSA":
                continue
            kid = key.get("kid")
            n_val = key.get("n")
            e_val = key.get("e")
            if not isinstance(kid, str) or not isinstance(n_val, str) or not isinstance(e_val, str):
                continue
            try:
                parsed[kid] = _RsaJwk(
                    kid=kid,
                    n=int.from_bytes(_base64url_decode(n_val), byteorder="big"),
                    e=int.from_bytes(_base64url_decode(e_val), byteorder="big"),
                    alg=str(key.get("alg") or "RS256"),
                )
            except (ValueError, binascii.Error):
                continue
        if not parsed:
            raise BaseAppException(
                error_code="AUTH_JWKS_INVALID",
                message="Unable to validate authentication token.",
                status_code=503,
            )
        return parsed

    def _refresh_jwks_if_needed(self) -> None:
        if not self._jwks_cache or self._is_cache_stale():
            self._jwks_cache = self._fetch_jwks()
            self._jwks_cached_at = time.time()

    def _verify_rs256_signature(self, signing_input: str, signature: bytes, jwk: _RsaJwk) -> bool:
        digest = hashlib.sha256(signing_input.encode("utf-8")).digest()
        digest_info = _PKCS1_SHA256_DIGEST_INFO_PREFIX + digest

        modulus_size = (jwk.n.bit_length() + 7) // 8
        sig_int = int.from_bytes(signature, byteorder="big")
        decrypted_int = pow(sig_int, jwk.e, jwk.n)
        em = decrypted_int.to_bytes(modulus_size, byteorder="big")

        if len(em) < len(digest_info) + 11:
            return False
        if not em.startswith(b"\x00\x01"):
            return False
        try:
            separator_index = em.index(b"\x00", 2)
        except ValueError:
            return False
        padding = em[2:separator_index]
        if len(padding) < 8 or any(byte != 0xFF for byte in padding):
            return False
        recovered = em[separator_index + 1 :]
        return hmac.compare_digest(recovered, digest_info)

    def verify(self, token: str) -> dict[str, Any]:
        token_parts = token.split(".")
        if len(token_parts) != 3:
            raise BaseAppException(
                error_code="AUTH_INVALID_TOKEN",
                message="Invalid authentication token.",
                status_code=401,
            )

        encoded_header, encoded_payload, encoded_signature = token_parts
        try:
            header = json.loads(_base64url_decode(encoded_header))
            payload = json.loads(_base64url_decode(encoded_payload))
            signature = _base64url_decode(encoded_signature)
        except (json.JSONDecodeError, ValueError, UnicodeDecodeError, binascii.Error) as exc:
            raise BaseAppException(
                error_code="AUTH_INVALID_TOKEN",
                message="Invalid authentication token.",
                status_code=401,
            ) from exc

        if not isinstance(header, dict) or not isinstance(payload, dict):
            raise BaseAppException(
                error_code="AUTH_INVALID_TOKEN",
                message="Invalid authentication token.",
                status_code=401,
            )

        alg = header.get("alg")
        kid = header.get("kid")
        if alg != "RS256" or not isinstance(kid, str):
            raise BaseAppException(
                error_code="AUTH_INVALID_TOKEN",
                message="Invalid authentication token.",
                status_code=401,
            )

        self._refresh_jwks_if_needed()
        jwk = self._jwks_cache.get(kid)
        if jwk is None:
            self._jwks_cache = self._fetch_jwks()
            self._jwks_cached_at = time.time()
            jwk = self._jwks_cache.get(kid)
        if jwk is None:
            raise BaseAppException(
                error_code="AUTH_UNKNOWN_KEY_ID",
                message="Invalid authentication token.",
                status_code=401,
            )

        signing_input = f"{encoded_header}.{encoded_payload}"
        if not self._verify_rs256_signature(signing_input=signing_input, signature=signature, jwk=jwk):
            raise BaseAppException(
                error_code="AUTH_INVALID_SIGNATURE",
                message="Invalid authentication token.",
                status_code=401,
            )

        now = int(time.time())
        leeway = settings.CLERK_JWT_LEEWAY_SECONDS
        exp = payload.get("exp")
        nbf = payload.get("nbf")
        iat = payload.get("iat")
        iss = payload.get("iss")
        aud = payload.get("aud")

        if not isinstance(exp, int) or now > exp + leeway:
            raise BaseAppException(
                error_code="AUTH_TOKEN_EXPIRED",
                message="Authentication token has expired.",
                status_code=401,
            )
        if isinstance(nbf, int) and now + leeway < nbf:
            raise BaseAppException(
                error_code="AUTH_TOKEN_NOT_YET_VALID",
                message="Authentication token is not yet valid.",
                status_code=401,
            )
        if isinstance(iat, int) and now + leeway < iat:
            raise BaseAppException(
                error_code="AUTH_TOKEN_NOT_YET_VALID",
                message="Authentication token is not yet valid.",
                status_code=401,
            )
        if not isinstance(iss, str) or iss != settings.CLERK_ISSUER:
            raise BaseAppException(
                error_code="AUTH_INVALID_ISSUER",
                message="Invalid authentication token.",
                status_code=401,
            )
        if settings.CLERK_AUDIENCE:
            if isinstance(aud, str):
                valid_aud = aud == settings.CLERK_AUDIENCE
            elif isinstance(aud, list):
                valid_aud = settings.CLERK_AUDIENCE in aud
            else:
                valid_aud = False
            if not valid_aud:
                raise BaseAppException(
                    error_code="AUTH_INVALID_AUDIENCE",
                    message="Invalid authentication token.",
                    status_code=401,
                )

        return payload


clerk_jwt_verifier = ClerkJWTVerifier()
