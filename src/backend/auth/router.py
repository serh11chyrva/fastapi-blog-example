from datetime import UTC, datetime, timedelta

from beanie import PydanticObjectId
from fastapi import APIRouter, HTTPException, Request, Response, status
from pymongo.errors import DuplicateKeyError

from backend.auth.schemas import AuthResponse, LoginRequest, RegisterRequest, SessionResponse
from backend.auth.service import AuthService
from backend.core.audit import record_audit, request_details
from backend.core.config import get_settings
from backend.core.dependencies import CurrentUser
from backend.core.rate_limit import enforce_rate_limit
from backend.core.security import hash_password, hash_session_token, new_session_token
from backend.auth.models import AuthIdentity, AuthSession
from backend.profiles.models import User


router = APIRouter(prefix="/auth", tags=["authentication"])


def _public_user(user: User) -> AuthResponse:
    return AuthResponse(id=str(user.id), email=user.email, username=user.username, display_name=user.display_name)


@router.get("/me", response_model=AuthResponse)
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
    client = request.app.state.mongo_client
    async with client.start_session() as db_session:
        async with await db_session.start_transaction():
            await auth_session.insert(session=db_session)
            if identity_to_upgrade is not None and identity_to_upgrade.password_hash is not None:
                await identity_to_upgrade.save(session=db_session)
            await record_audit(request, action, actor_id=user.id, target_type="session", target_id=str(auth_session.id), session=db_session)
    return token, auth_session


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, request: Request, response: Response) -> AuthResponse:
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
        password_hash=hash_password(payload.password),
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
    client = request.app.state.mongo_client
    try:
        async with client.start_session() as db_session:
            async with await db_session.start_transaction():
                await user.insert(session=db_session)
                await identity.insert(session=db_session)
                await auth_session.insert(session=db_session)
                await record_audit(
                    request,
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


@router.post("/login", response_model=AuthResponse)
async def login(payload: LoginRequest, request: Request, response: Response) -> AuthResponse:
    normalized = payload.identifier.strip().lower().removeprefix("@")
    await enforce_rate_limit(request, "login", normalized, limit=8, window_seconds=600)
    authentication = await AuthService().authenticate_password(payload.identifier, payload.password)
    user, identity = authentication.user, authentication.identity
    if not authentication.authenticated or user is None or identity is None:
        await record_audit(
            request,
            "LOGIN_FAILED",
            actor_id=user.id if user else None,
            target_type="user" if user else None,
            target_id=str(user.id) if user else None,
            metadata={"identifier_type": "email" if "@" in normalized and not payload.identifier.strip().startswith("@") else "username"},
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username/email or password")

    token, _ = await _create_session(
        request,
        user,
        "LOGIN_SUCCEEDED",
        identity if authentication.needs_rehash else None,
    )
    _set_session_cookie(response, token)
    return _public_user(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(request: Request, response: Response, current_user: CurrentUser) -> Response:
    auth_session: AuthSession = request.state.auth_session
    now = datetime.now(UTC)
    client = request.app.state.mongo_client
    async with client.start_session() as db_session:
        async with await db_session.start_transaction():
            auth_session.revoked_at = now
            await auth_session.save(session=db_session)
            await record_audit(request, "LOGOUT", actor_id=current_user.id, target_type="session", target_id=str(auth_session.id), session=db_session)
    _clear_session_cookie(response)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/sessions", response_model=list[SessionResponse])
async def list_sessions(request: Request, current_user: CurrentUser) -> list[SessionResponse]:
    now = datetime.now(UTC)
    sessions = await AuthSession.find(
        AuthSession.user_id == current_user.id,
        AuthSession.revoked_at == None,  # noqa: E711
        AuthSession.expires_at > now,
        AuthSession.last_seen_at > now - timedelta(days=get_settings().session_idle_days),
    ).sort(-AuthSession.last_seen_at).to_list()
    current_id = request.state.auth_session.id
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


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_session(session_id: str, request: Request, response: Response, current_user: CurrentUser) -> Response:
    if not PydanticObjectId.is_valid(session_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    auth_session = await AuthSession.get(PydanticObjectId(session_id))
    if auth_session is None or auth_session.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    if auth_session.revoked_at is None:
        now = datetime.now(UTC)
        client = request.app.state.mongo_client
        async with client.start_session() as db_session:
            async with await db_session.start_transaction():
                auth_session.revoked_at = now
                await auth_session.save(session=db_session)
                await record_audit(request, "SESSION_REVOKED", actor_id=current_user.id, target_type="session", target_id=session_id, session=db_session)
    if request.state.auth_session.id == auth_session.id:
        _clear_session_cookie(response)
        response.status_code = status.HTTP_204_NO_CONTENT
        return response
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/sessions/logout-others", status_code=status.HTTP_204_NO_CONTENT)
async def logout_other_sessions(request: Request, current_user: CurrentUser) -> Response:
    now = datetime.now(UTC)
    current_id = request.state.auth_session.id
    sessions = await AuthSession.find(
        AuthSession.user_id == current_user.id,
        AuthSession.revoked_at == None,  # noqa: E711
        AuthSession.id != current_id,
        AuthSession.expires_at > now,
    ).to_list()
    client = request.app.state.mongo_client
    async with client.start_session() as db_session:
        async with await db_session.start_transaction():
            for item in sessions:
                item.revoked_at = now
                await item.save(session=db_session)
            await record_audit(
                request,
                "OTHER_SESSIONS_REVOKED",
                actor_id=current_user.id,
                target_type="user",
                target_id=str(current_user.id),
                metadata={"revoked_count": len(sessions)},
                session=db_session,
            )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
