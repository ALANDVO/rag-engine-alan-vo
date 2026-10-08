import base64
import hashlib
import time
from typing import Any, Dict, List, Optional
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
import httpx
from app.core.config import settings

security_bearer = HTTPBearer(auto_error=False)

# Role hierarchy
ROLE_LEVELS = {
    "viewer": 1,
    "operator": 2,
    "admin": 3,
}

_jwks_cache: Dict[str, Any] = {}
_jwks_cached_at: float = 0.0


def compute_pkce_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest).decode("utf-8").rstrip("=")


def verify_pkce(verifier: str, challenge: str) -> bool:
    expected = compute_pkce_challenge(verifier)
    return expected == challenge


def create_demo_token(user_id: str, role: str, expires_in_seconds: int = 3600) -> str:
    if not settings.demo_mode:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Demo mode is disabled."
        )
    now = int(time.time())
    payload = {
        "sub": user_id,
        "iss": "demo-authority",
        "aud": settings.oidc_audience,
        "iat": now,
        "exp": now + expires_in_seconds,
        "roles": [role],
        "demo": True,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


async def fetch_keycloak_jwks() -> Dict[str, Any]:
    global _jwks_cache, _jwks_cached_at
    now = time.time()
    if _jwks_cache and (now - _jwks_cached_at) < 300:
        return _jwks_cache

    certs_url = f"{settings.oidc_issuer_url.rstrip('/')}/protocol/openid-connect/certs"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(certs_url)
            if resp.status_code == 200:
                _jwks_cache = resp.json()
                _jwks_cached_at = now
                return _jwks_cache
    except Exception:
        pass
    return _jwks_cache


async def decode_token(token: str) -> Dict[str, Any]:
    # First check if this is a signed demo token
    if settings.demo_mode:
        try:
            unverified = jwt.get_unverified_claims(token)
            if unverified.get("demo") is True:
                payload = jwt.decode(
                    token,
                    settings.jwt_secret,
                    algorithms=["HS256"],
                    audience=settings.oidc_audience,
                    issuer="demo-authority",
                )
                return payload
        except JWTError:
            pass

    # Standard OIDC / Keycloak JWT verification
    jwks = await fetch_keycloak_jwks()
    if not jwks or "keys" not in jwks:
        # If JWKS is not reachable or empty, verify using configured secret or raise
        try:
            payload = jwt.decode(
                token,
                settings.jwt_secret,
                algorithms=["HS256", "RS256"],
                audience=settings.oidc_audience,
                options={"verify_aud": False},
            )
            return payload
        except JWTError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token signature or expired credentials.",
                headers={"WWW-Authenticate": "Bearer"},
            )

    try:
        header = jwt.get_unverified_header(token)
        kid = header.get("kid")
        key = next((k for k in jwks["keys"] if k.get("kid") == kid), None)
        if not key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unable to find matching token key in Keycloak JWKS.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        payload = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            audience=settings.oidc_audience,
            issuer=settings.oidc_issuer_url,
        )
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token validation failed: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security_bearer),
) -> Dict[str, Any]:
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Bearer authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    payload = await decode_token(token)

    # Extract roles from token claims
    roles: List[str] = []
    if "roles" in payload and isinstance(payload["roles"], list):
        roles.extend(payload["roles"])
    if "realm_access" in payload and isinstance(payload["realm_access"], dict):
        realm_roles = payload["realm_access"].get("roles", [])
        if isinstance(realm_roles, list):
            roles.extend(realm_roles)

    # Determine highest effective role
    effective_role = "viewer"
    for r in ["admin", "operator", "viewer"]:
        if r in roles:
            effective_role = r
            break

    return {
        "user_id": payload.get("sub", "unknown"),
        "username": payload.get("preferred_username", payload.get("sub", "user")),
        "roles": roles,
        "effective_role": effective_role,
        "is_demo": payload.get("demo", False),
    }


def require_role(min_role: str):
    min_level = ROLE_LEVELS.get(min_role, 1)

    async def role_checker(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        user_level = ROLE_LEVELS.get(user.get("effective_role", "viewer"), 1)
        if user_level < min_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required role: {min_role}",
            )
        return user

    return role_checker
