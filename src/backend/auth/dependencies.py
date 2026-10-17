from datetime import UTC, datetime, timedelta
from typing import Annotated, cast

from beanie.odm.queries.update import UpdateResponse
from fastapi import Depends, HTTPException, Request, Security, status
from fastapi.security import APIKeyCookie

from backend.auth.models import AuthSession
from backend.auth.security import hash_session_token
from backend.core.config import get_settings, session_cookie_name
from backend.profiles.models import User

session_cookie = APIKeyCookie(
    name=session_cookie_name(),
    scheme_name="SessionCookie",
    auto_error=False,
    description="HttpOnly session cookie issued by registration or login.",
)
SessionToken = Annotated[str | None, Security(session_cookie)]


async def get_current_user(request: Request, token: SessionToken) -> User:
    """Resolve a session and atomically record activity without undoing revocation.

    Absolute and idle deadlines must both remain valid at the activity update.
    The refreshed session and account are available on request.state afterwards.
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required"
        )

    now = datetime.now(UTC)
    auth_session = await AuthSession.find_one(
        AuthSession.token_hash == hash_session_token(token)
    )
    if auth_session is None or auth_session.revoked_at is not None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Session is invalid"
        )
    if (
        auth_session.expires_at <= now
        or auth_session.last_seen_at + timedelta(days=get_settings().session_idle_days)
        <= now
    ):
        await AuthSession.find_one(
            {
                "_id": auth_session.id,
                "revoked_at": None,
                "$or": [
                    {"expires_at": {"$lte": now}},
                    {
                        "last_seen_at": {
                            "$lte": now
                            - timedelta(days=get_settings().session_idle_days)
                        }
                    },
                ],
            }
        ).update({"$set": {"revoked_at": now}})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Session has expired"
        )

    user = await User.get(auth_session.user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Account is unavailable"
        )

    now = datetime.now(UTC)
    ip_address = request.headers.get("x-real-ip") or (
        request.client.host if request.client else None
    )
    auth_session = await AuthSession.find_one(
        {
            "_id": auth_session.id,
            "revoked_at": None,
            "expires_at": {"$gt": now},
            "last_seen_at": {
                "$gt": now - timedelta(days=get_settings().session_idle_days)
            },
        }
    ).update(
        {
            "$max": {"last_seen_at": now},
            "$set": {
                "ip_address": ip_address,
                "user_agent": request.headers.get("user-agent", "")[:512] or None,
            },
        },
        response_type=UpdateResponse.NEW_DOCUMENT,
    )
    if auth_session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Session is invalid"
        )
    request.state.auth_session = auth_session
    request.state.current_user = user
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def get_optional_user(request: Request, token: SessionToken) -> User | None:
    if not token:
        return None
    try:
        return await get_current_user(request, token)
    except HTTPException as exc:
        if exc.status_code == status.HTTP_401_UNAUTHORIZED:
            return None
        raise


OptionalUser = Annotated[User | None, Depends(get_optional_user)]


def get_session(request: Request) -> AuthSession:
    """Read the typed session populated by the cached CurrentUser dependency."""
    return cast(AuthSession, request.state.auth_session)
