from fastapi import APIRouter, Request, Response, status
from starlette.concurrency import run_in_threadpool

from backend.api.metadata import Origin, SessionId, documented_responses
from backend.audit.dependencies import audit_context
from backend.auth.accounts import AccountService
from backend.auth.dependencies import CurrentUser, get_session
from backend.auth.presentation import present_sessions
from backend.auth.rate_limit import enforce_rate_limit
from backend.auth.schemas import (
    AuthResponse,
    LoginRequest,
    RegisterRequest,
    SessionResponse,
)
from backend.auth.sessions import SessionService
from backend.core.config import get_settings
from backend.core.resources import get_resources
from backend.profiles.models import User

router = APIRouter(prefix="/auth")


def _public_user(user: User) -> AuthResponse:
    return AuthResponse(
        id=str(user.id),
        email=user.email,
        username=user.username,
        display_name=user.display_name,
    )


@router.get(
    "/me",
    response_model=AuthResponse,
    summary="Get the current account",
    description="Returns the account associated with the current session cookie.",
    tags=["Authentication"],
    responses=documented_responses(401, 503),
)
async def get_me(current_user: CurrentUser) -> AuthResponse:
    return _public_user(current_user)


def _set_session_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        settings.session_cookie_name,
        token,
        max_age=settings.session_absolute_days * 24 * 60 * 60,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
        path="/",
    )


def _clear_session_cookie(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(
        settings.session_cookie_name,
        path="/",
        secure=settings.session_cookie_secure,
        httponly=True,
        samesite="lax",
    )


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register and start a session",
    description=(
        "Creates an account with a unique email and public username, then starts a session "
        "and sets the HttpOnly cookie. Returns 409 if the email or username is already taken. "
        "Accepts client_type (web by default, mobile, or desktop) and an optional device_name "
        "for apps. Limited to five attempts per hour per IP address and email."
    ),
    tags=["Authentication"],
    responses=documented_responses(403, 409, 429, 503),
)
async def register(
    _origin: Origin,
    payload: RegisterRequest,
    request: Request,
    response: Response,
) -> AuthResponse:
    await enforce_rate_limit(
        request, "register", payload.email, limit=5, window_seconds=3600
    )
    user, token = await AccountService(
        get_resources(request), audit_context(request)
    ).register(payload)
    _set_session_cookie(response, token)
    return _public_user(user)


@router.post(
    "/login",
    response_model=AuthResponse,
    summary="Log in",
    description=(
        "Accepts an email address or username, optionally prefixed with @. Successful login "
        "sets the HttpOnly session cookie and returns the account. Limited to eight attempts "
        "per ten minutes per IP address and identifier. Accepts client_type (web by default, "
        "mobile, or desktop) and an optional device_name for apps."
    ),
    tags=["Authentication"],
    responses=documented_responses(401, 403, 409, 429, 503),
)
async def login(
    _origin: Origin, payload: LoginRequest, request: Request, response: Response
) -> AuthResponse:
    normalized = payload.identifier.strip().lower().removeprefix("@")
    await enforce_rate_limit(request, "login", normalized, limit=8, window_seconds=600)
    user, token = await AccountService(
        get_resources(request), audit_context(request)
    ).login(payload)
    _set_session_cookie(response, token)
    return _public_user(user)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Log out this session",
    description="Revokes the current session and clears the cookie.",
    tags=["Authentication"],
    responses=documented_responses(401, 403, 409, 503),
)
async def logout(
    _origin: Origin, request: Request, response: Response, current_user: CurrentUser
) -> Response:
    await SessionService(get_resources(request), audit_context(request)).revoke(
        current_user, str(get_session(request).id), action="LOGOUT"
    )
    _clear_session_cookie(response)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get(
    "/sessions",
    response_model=list[SessionResponse],
    summary="List active sessions",
    description=(
        "Returns your unrevoked, unexpired sessions, most recently active first. Includes the "
        "client category, approximate location of the latest recorded IP, formatted device "
        "(browser and OS for web), absolute expiry, and a flag identifying the current session. "
        "Raw IP addresses and User-Agents are not returned."
    ),
    tags=["Sessions"],
    responses=documented_responses(401, 503),
)
async def list_sessions(
    request: Request, current_user: CurrentUser
) -> list[SessionResponse]:
    sessions = await SessionService(
        get_resources(request), audit_context(request)
    ).active(current_user)
    current_id = get_session(request).id
    return await run_in_threadpool(
        present_sessions, sessions, str(current_id), get_resources(request).geoip
    )


@router.delete(
    "/sessions/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke a session",
    description="Revokes one of your sessions. Unknown and other users' sessions both return 404.",
    tags=["Sessions"],
    responses=documented_responses(401, 403, 404, 409, 503),
)
async def revoke_session(
    _origin: Origin,
    session_id: SessionId,
    request: Request,
    response: Response,
    current_user: CurrentUser,
) -> Response:
    await SessionService(get_resources(request), audit_context(request)).revoke(
        current_user, session_id
    )
    if str(get_session(request).id) == session_id.lower():
        _clear_session_cookie(response)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.post(
    "/sessions/logout-others",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Log out other sessions",
    description="Revokes every active session except the cookie used for this request.",
    tags=["Sessions"],
    responses=documented_responses(401, 403, 409, 503),
)
async def logout_other_sessions(
    _origin: Origin, request: Request, current_user: CurrentUser
) -> Response:
    await SessionService(get_resources(request), audit_context(request)).revoke_others(
        current_user, get_session(request).id
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
