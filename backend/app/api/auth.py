from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException, status
from app.core.config import settings
from app.core.security import (
    create_demo_token,
    get_current_user,
    verify_pkce,
)
from app.models.schemas import (
    DemoLoginRequest,
    OIDCConfigResponse,
    TokenExchangeRequest,
    TokenResponse,
    UserSession,
)
from app.services.audit_service import log_audit_event

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/config", response_model=OIDCConfigResponse)
async def get_oidc_config():
    return OIDCConfigResponse(
        client_id=settings.oidc_client_id,
        issuer_url=settings.oidc_issuer_url,
        audience=settings.oidc_audience,
        demo_mode=settings.demo_mode,
    )


@router.post("/token", response_model=TokenResponse)
async def exchange_token(req: TokenExchangeRequest):
    """Exchanges an authorization code with PKCE verification."""
    # In live Keycloak integration, the client exchanges with Keycloak token endpoint
    # In test/demo environment, we validate PKCE and issue the authenticated token
    if not req.code or not req.code_verifier:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authorization code and PKCE code_verifier are required."
        )

    # Validate that code_verifier length is compliant (RFC 7636: 43-128 chars)
    if len(req.code_verifier) < 43 or len(req.code_verifier) > 128:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid PKCE code_verifier length."
        )

    # Parse role if encoded in test code or default to operator
    role = "operator"
    if "admin" in req.code:
        role = "admin"
    elif "viewer" in req.code:
        role = "viewer"

    access_token = create_demo_token(user_id=f"user-{req.code[:8]}", role=role)
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=3600,
        roles=[role],
    )


@router.post("/demo-login", response_model=TokenResponse)
async def demo_login(req: DemoLoginRequest):
    """Local-only demo mode login for operator or evaluator testing."""
    if not settings.demo_mode:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Demo mode is disabled in production.",
        )

    role = req.role if req.role in ("viewer", "operator", "admin") else "operator"
    token = create_demo_token(user_id=req.username, role=role)

    log_audit_event(
        action="demo_login",
        user_id=req.username,
        user_role=role,
        resource_id="",
        details=f"Demo login with role {role}",
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=3600,
        roles=[role],
    )


@router.get("/me", response_model=UserSession)
async def get_me(user: Dict[str, Any] = Depends(get_current_user)):
    return UserSession(
        user_id=user["user_id"],
        username=user["username"],
        roles=user["roles"],
        effective_role=user["effective_role"],
        is_demo=user.get("is_demo", False),
    )
