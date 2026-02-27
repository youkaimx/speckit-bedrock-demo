"""OAuth/Cognito authentication middleware: validate Bearer token, extract owner_id."""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

# In production, validate JWT against Cognito (e.g. jose + JWKS or Cognito API).
# For now we accept a Bearer token and treat the first segment (or a fixed claim) as owner_id.
# Full Cognito validation: decode JWT, verify signature with Cognito JWKS, extract "sub" as owner_id.

security = HTTPBearer(auto_error=False)


def _decode_owner_id(credentials: HTTPAuthorizationCredentials | None) -> str | None:
    """Extract owner_id from Bearer token. Only accepts dev- tokens or JWT with sub/owner_id claim."""
    if not credentials or not credentials.credentials:
        return None
    token = credentials.credentials.strip()
    if not token:
        return None
    # Dev token: explicit prefix for local development only
    if token.startswith("dev-"):
        return token
    # JWT: must have 3 segments and decode to a payload with sub or owner_id
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        import base64
        import json

        payload_b64 = parts[1]
        payload_b64 += "=" * (4 - len(payload_b64) % 4)  # padding for urlsafe_b64decode
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))
        if not isinstance(payload, dict):
            return None
        owner = payload.get("sub") or payload.get("owner_id")
        if owner is None or not str(owner).strip():
            return None
        return str(owner).strip()
    except Exception:
        return None


async def get_owner_id(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
) -> str:
    """Dependency: require valid Bearer token and return owner_id. Raises 401 if missing/invalid."""
    owner_id = _decode_owner_id(credentials)
    if not owner_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization token",
        )
    return owner_id


async def get_owner_id_optional(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
) -> str | None:
    """Dependency: return owner_id if token present, else None."""
    return _decode_owner_id(credentials)


class AuthMiddleware(BaseHTTPMiddleware):
    """Set request.state.owner_id from Bearer token when present (for rate limit middleware)."""

    async def dispatch(self, request: Request, call_next):
        auth = request.headers.get("Authorization")
        request.state.owner_id = decode_owner_id_from_header(auth)
        return await call_next(request)


def decode_owner_id_from_header(authorization: str | None) -> str | None:
    """Decode owner_id from Authorization header (for middleware). Returns None if missing/invalid."""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization[7:].strip()
    if not token:
        return None
    # Dev token: explicit prefix for local development only
    if token.startswith("dev-"):
        return token
    # JWT: must have 3 segments and decode to a payload with sub or owner_id
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        import base64
        import json

        payload_b64 = parts[1]
        payload_b64 += "=" * (4 - len(payload_b64) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))
        if not isinstance(payload, dict):
            return None
        owner = payload.get("sub") or payload.get("owner_id")
        if owner is None or not str(owner).strip():
            return None
        return str(owner).strip()
    except Exception:
        return None
