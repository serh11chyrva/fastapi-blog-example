from backend.core.api_metadata import documented_responses, Origin, SessionId
from backend.core.transactions import transaction
from backend.core.resources import get_resources
from datetime import UTC, datetime, timedelta

from beanie import PydanticObjectId
from fastapi import APIRouter, HTTPException, Request, Response, status
from pymongo.errors import DuplicateKeyError

from backend.auth.schemas import AuthResponse, LoginRequest, RegisterRequest, SessionResponse
from backend.auth.service import AuthService, PasswordRejected
from backend.audit.service import record_audit
from backend.audit.dependencies import audit_context, request_details
from backend.core.config import get_settings
from backend.auth.dependencies import CurrentUser, get_session
from backend.auth.rate_limit import enforce_rate_limit
from backend.auth.security import hash_password_async, hash_session_token, new_session_token
from backend.auth.models import AuthIdentity, AuthSession
from backend.profiles.models import User


router = APIRouter(prefix="/auth")


def _public_user(user: User) -> AuthResponse:
    return AuthResponse(id=str(user.id), email=user.email, username=user.username, display_name=user.display_name)


@router.get(
    "/me",
    response_model=AuthResponse,
    summary='Get the current account',
    description='Returns the account associated with the current session cookie.',
    tags=['Authentication'],
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
    response.delete_cookie(settings.session_cookie_name, path="/", secure=settings.session_cookie_secure, httponly=True, samesite="lax")


async def _create_session(
    request: Request,
    user: User,
    action: str,
    identity_to_upgrade: AuthIdentity | None = None,
) -> tuple[str, AuthSession]:
    now = datetime.now(UTC)
    token = new_session_token()
    ip_address, user_agent = request_details(request)
    absolute_expires = now + timedelta(days=get_settings().session_absolute_days)
    auth_session = AuthSession(
        user_id=user.id,
        token_hash=hash_session_token(token),
        created_at=now,
        last_seen_at=now,
        expires_at=absolute_expires,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    client = get_resources(request).mongo
    async with transaction(client) as db_session:
        await auth_session.insert(session=db_session)
        if identity_to_upgrade is not None and identity_to_upgrade.password_hash is not None:
            await identity_to_upgrade.save(session=db_session)
        await record_audit(audit_context(request), action, actor_id=user.id, target_type="session", target_id=str(auth_session.id), session=db_session)
    return token, auth_session


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary='Register and start a session',
    description=(
        'Creates an account with a unique email and public username, then starts a session '
        'and sets the HttpOnly cookie. Returns 409 if the email or username is already taken. '
        'Limited to five attempts per hour per IP address and email.'
    ),
    tags=['Authentication'],
    responses=documented_responses(403, 409, 429, 503),
)
async def register(_origin: Origin, payload: RegisterRequest, request: Request, response: Response) -> AuthResponse:
    await enforce_rate_limit(request, "register", payload.email, limit=5, window_seconds=3600)
    now = datetime.now(UTC)
    user = User(
        id=PydanticObjectId(),
        email=str(payload.email).lower(),
        username=payload.username,
        display_name=payload.display_name,
        created_at=now,
        updated_at=now,
    )
    identity = AuthIdentity(
        user_id=user.id,
        provider="password",
        subject=str(user.id),
        password_hash=await hash_password_async(payload.password),
        created_at=now,
    )
    token = new_session_token()
    ip_address, user_agent = request_details(request)
    auth_session = AuthSession(
        user_id=user.id,
        token_hash=hash_session_token(token),
        created_at=now,
        last_seen_at=now,
        expires_at=now + timedelta(days=get_settings().session_absolute_days),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    client = get_resources(request).mongo
    try:
        async with transaction(client) as db_session:
            await user.insert(session=db_session)
            await identity.insert(session=db_session)
            await auth_session.insert(session=db_session)
            await record_audit(
                audit_context(request),
                "USER_REGISTERED",
                actor_id=user.id,
                target_type="user",
                target_id=str(user.id),
                session=db_session,
            )
    except DuplicateKeyError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email or username is already in use") from exc
    _set_session_cookie(response, token)
    return _public_user(user)


@router.post(
    "/login",
    response_model=AuthResponse,
    summary='Log in',
    description=(
        'Accepts an email address or username, optionally prefixed with @. Successful login '
        'sets the HttpOnly session cookie and returns the account. Limited to eight attempts '
        'per ten minutes per IP address and identifier.'
    ),
    tags=['Authentication'],
    responses=documented_responses(401, 403, 409, 429, 503),
)
async def login(_origin: Origin, payload: LoginRequest, request: Request, response: Response) -> AuthResponse:
    normalized = payload.identifier.strip().lower().removeprefix("@")
    await enforce_rate_limit(request, "login", normalized, limit=8, window_seconds=600)
    authentication = await AuthService().authenticate_password(payload.identifier, payload.password)
    if isinstance(authentication, PasswordRejected):
        user = authentication.user
        await record_audit(
            audit_context(request),
            "LOGIN_FAILED",
            actor_id=user.id if user else None,
            target_type="user" if user else None,
            target_id=str(user.id) if user else None,
            metadata={"identifier_type": "email" if "@" in normalized and not payload.identifier.strip().startswith("@") else "username"},
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username/email or password")

    user, identity = authentication.user, authentication.identity
    token, _ = await _create_session(
        request,
        user,
        "LOGIN_SUCCEEDED",
        identity if authentication.needs_rehash else None,
    )
    _set_session_cookie(response, token)
    return _public_user(user)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary='Log out this session',
    description='Revokes the current session and clears the cookie.',
    tags=['Authentication'],
    responses=documented_responses(401, 403, 409, 503),
)
async def logout(_origin: Origin, request: Request, response: Response, current_user: CurrentUser) -> Response:
    auth_session: AuthSession = get_session(request)
    now = datetime.now(UTC)
    client = get_resources(request).mongo
    async with transaction(client) as db_session:
        await auth_session.set({AuthSession.revoked_at: now}, session=db_session)
        await record_audit(audit_context(request), "LOGOUT", actor_id=current_user.id, target_type="session", target_id=str(auth_session.id), session=db_session)
    _clear_session_cookie(response)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get(
    "/sessions",
    response_model=list[SessionResponse],
    summary='List active sessions',
    description=(
        'Returns your unrevoked, unexpired sessions, most recently active first. Includes the '
        'latest recorded IP address and User-Agent, absolute expiry, and a flag identifying '
        'the current session.'
    ),
    tags=['Sessions'],
    responses=documented_responses(401, 503),
)
async def list_sessions(request: Request, current_user: CurrentUser) -> list[SessionResponse]:
    now = datetime.now(UTC)
    sessions = await AuthSession.find(
        AuthSession.user_id == current_user.id,
        AuthSession.revoked_at == None,  # noqa: E711
        AuthSession.expires_at > now,
        AuthSession.last_seen_at > now - timedelta(days=get_settings().session_idle_days),
    ).sort(-AuthSession.last_seen_at).to_list()
    current_id = get_session(request).id
    return [
        SessionResponse(
            id=str(item.id),
            created_at=item.created_at,
            last_seen_at=item.last_seen_at,
            expires_at=item.expires_at,
            ip_address=item.ip_address,
            user_agent=item.user_agent,
            current=item.id == current_id,
        )
        for item in sessions
    ]


@router.delete(
    "/sessions/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary='Revoke a session',
    description="Revokes one of your sessions. Unknown and other users' sessions both return 404.",
    tags=['Sessions'],
    responses=documented_responses(401, 403, 404, 409, 503),
)
async def revoke_session(_origin: Origin, session_id: SessionId, request: Request, response: Response, current_user: CurrentUser) -> Response:
    if not PydanticObjectId.is_valid(session_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    auth_session = await AuthSession.get(PydanticObjectId(session_id))
    if auth_session is None or auth_session.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    if auth_session.revoked_at is None:
        now = datetime.now(UTC)
        client = get_resources(request).mongo
        async with transaction(client) as db_session:
            await auth_session.set({AuthSession.revoked_at: now}, session=db_session)
            await record_audit(audit_context(request), "SESSION_REVOKED", actor_id=current_user.id, target_type="session", target_id=session_id, session=db_session)
    if get_session(request).id == auth_session.id:
        _clear_session_cookie(response)
        response.status_code = status.HTTP_204_NO_CONTENT
        return response
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/sessions/logout-others",
    status_code=status.HTTP_204_NO_CONTENT,
    summary='Log out other sessions',
    description='Revokes every active session except the cookie used for this request.',
    tags=['Sessions'],
    responses=documented_responses(401, 403, 409, 503),
)
async def logout_other_sessions(_origin: Origin, request: Request, current_user: CurrentUser) -> Response:
    now = datetime.now(UTC)
    current_id = get_session(request).id
    sessions = await AuthSession.find(
        AuthSession.user_id == current_user.id,
        AuthSession.revoked_at == None,  # noqa: E711
        AuthSession.id != current_id,
        AuthSession.expires_at > now,
    ).to_list()
    client = get_resources(request).mongo
    async with transaction(client) as db_session:
        for item in sessions:
            await item.set({AuthSession.revoked_at: now}, session=db_session)
        await record_audit(
            audit_context(request),
            "OTHER_SESSIONS_REVOKED",
            actor_id=current_user.id,
            target_type="user",
            target_id=str(current_user.id),
            metadata={"revoked_count": len(sessions)},
            session=db_session,
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
