import asyncio
import json
import time
from dataclasses import dataclass
from typing import Any

import httpx
import jwt
from jwt import InvalidTokenError
from jwt.algorithms import RSAAlgorithm

from app.core.config import settings
from app.core.exceptions import BaseAppException


@dataclass(frozen=True)
class _CachedJwk:
    kid: str
    key: Any


class ClerkJWTVerifier:
    def __init__(self) -> None:
        self._jwks_cache: dict[str, _CachedJwk] = {}
        self._jwks_cached_at: float = 0.0
        self._lock = asyncio.Lock()

    def _is_cache_stale(self) -> bool:
        return (time.time() - self._jwks_cached_at) > settings.CLERK_JWKS_CACHE_TTL_SECONDS

    async def _fetch_jwks(self) -> dict[str, _CachedJwk]:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(settings.CLERK_JWKS_URL)
                response.raise_for_status()
                payload = response.json()
        except (httpx.HTTPError, json.JSONDecodeError, ValueError) as exc:
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

        parsed: dict[str, _CachedJwk] = {}
        for key_dict in keys:
            if not isinstance(key_dict, dict):
                continue
            kid = key_dict.get("kid")
            if not isinstance(kid, str):
                continue
            try:
                public_key = RSAAlgorithm.from_jwk(json.dumps(key_dict))
            except (ValueError, TypeError):
                continue
            parsed[kid] = _CachedJwk(kid=kid, key=public_key)

        if not parsed:
            raise BaseAppException(
                error_code="AUTH_JWKS_INVALID",
                message="Unable to validate authentication token.",
                status_code=503,
            )
        return parsed

    async def _refresh_jwks_if_needed(self) -> None:
        if self._jwks_cache and not self._is_cache_stale():
            return
        async with self._lock:
            if self._jwks_cache and not self._is_cache_stale():
                return
            self._jwks_cache = await self._fetch_jwks()
            self._jwks_cached_at = time.time()

    async def _resolve_key(self, kid: str) -> Any:
        await self._refresh_jwks_if_needed()
        cached = self._jwks_cache.get(kid)
        if cached is not None:
            return cached.key

        async with self._lock:
            self._jwks_cache = await self._fetch_jwks()
            self._jwks_cached_at = time.time()
            cached = self._jwks_cache.get(kid)
        if cached is None:
            raise BaseAppException(
                error_code="AUTH_UNKNOWN_KEY_ID",
                message="Invalid authentication token.",
                status_code=401,
            )
        return cached.key

    async def verify(self, token: str) -> dict[str, Any]:
        try:
            header = jwt.get_unverified_header(token)
        except InvalidTokenError as exc:
            raise BaseAppException(
                error_code="AUTH_INVALID_TOKEN",
                message="Invalid authentication token.",
                status_code=401,
            ) from exc

        kid = header.get("kid")
        alg = header.get("alg")
        if not isinstance(kid, str) or alg != "RS256":
            raise BaseAppException(
                error_code="AUTH_INVALID_TOKEN",
                message="Invalid authentication token.",
                status_code=401,
            )

        key = await self._resolve_key(kid)

        options = {
            "require": ["exp", "iat", "iss", "sub"],
            "verify_signature": True,
            "verify_exp": True,
            "verify_iat": True,
            "verify_nbf": True,
            "verify_aud": settings.CLERK_AUDIENCE is not None,
            "verify_iss": True,
            "verify_sub": True,
        }
        try:
            decoded = jwt.decode(
                token,
                key=key,
                algorithms=["RS256"],
                issuer=settings.CLERK_ISSUER,
                audience=settings.CLERK_AUDIENCE,
                options=options,
                leeway=settings.CLERK_JWT_LEEWAY_SECONDS,
            )
        except InvalidTokenError as exc:
            if isinstance(exc, jwt.ExpiredSignatureError):
                error_code = "AUTH_TOKEN_EXPIRED"
                message = "Authentication token has expired."
            else:
                error_code = "AUTH_INVALID_TOKEN"
                message = "Invalid authentication token."
            raise BaseAppException(
                error_code=error_code,
                message=message,
                status_code=401,
            ) from exc

        if not isinstance(decoded, dict):
            raise BaseAppException(
                error_code="AUTH_INVALID_TOKEN",
                message="Invalid authentication token.",
                status_code=401,
            )
        return decoded


clerk_jwt_verifier = ClerkJWTVerifier()
