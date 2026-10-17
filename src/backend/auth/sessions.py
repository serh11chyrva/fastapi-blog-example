"""Session persistence and audited revocation, independent of HTTP cookies."""

from datetime import UTC, datetime, timedelta

from beanie import PydanticObjectId

from backend.audit.context import AuditContext
from backend.audit.service import record_audit
from backend.auth.client import ClientType
from backend.auth.models import AuthIdentity, AuthSession
from backend.auth.security import hash_session_token, new_session_token
from backend.core.config import get_settings
from backend.core.errors import NotFound
from backend.core.resources import AppResources
from backend.core.transactions import transaction
from backend.profiles.models import User


def prepare_session(
    user: User,
    context: AuditContext,
    now: datetime,
    *,
    client_type: ClientType = ClientType.WEB,
    device_name: str | None = None,
) -> tuple[str, AuthSession]:
    token = new_session_token()
    return token, AuthSession(
        user_id=user.id,
        token_hash=hash_session_token(token),
        created_at=now,
        last_seen_at=now,
        expires_at=now + timedelta(days=get_settings().session_absolute_days),
        ip_address=context.ip_address,
        user_agent=context.user_agent,
        client_type=client_type,
        device_name=device_name if client_type != ClientType.WEB else None,
    )


class SessionService:
    def __init__(self, resources: AppResources, audit: AuditContext) -> None:
        self.resources = resources
        self.audit = audit

    async def create(
        self,
        user: User,
        identity_to_upgrade: AuthIdentity | None = None,
        *,
        client_type: ClientType = ClientType.WEB,
        device_name: str | None = None,
    ) -> str:
        """Persist the session, optional password upgrade, and audit atomically."""
        token, session = prepare_session(
            user,
            self.audit,
            datetime.now(UTC),
            client_type=client_type,
            device_name=device_name,
        )
        async with transaction(self.resources.mongo) as db_session:
            await session.insert(session=db_session)
            if identity_to_upgrade is not None:
                await identity_to_upgrade.set(
                    {AuthIdentity.password_hash: identity_to_upgrade.password_hash},
                    session=db_session,
                )
            await record_audit(
                self.audit,
                "LOGIN_SUCCEEDED",
                actor_id=user.id,
                target_type="session",
                target_id=str(session.id),
                session=db_session,
            )
        return token

    async def active(self, owner: User) -> list[AuthSession]:
        now = datetime.now(UTC)
        return (
            await AuthSession.find(
                {
                    "user_id": owner.id,
                    "revoked_at": None,
                    "expires_at": {"$gt": now},
                    "last_seen_at": {
                        "$gt": now - timedelta(days=get_settings().session_idle_days)
                    },
                }
            )
            .sort(("last_seen_at", -1), ("_id", -1))
            .to_list()
        )

    async def revoke(
        self, owner: User, session_id: str, *, action: str = "SESSION_REVOKED"
    ) -> None:
        """Revoke only an owned session, preserving all activity fields."""
        if not PydanticObjectId.is_valid(session_id):
            raise NotFound("Session not found")
        async with transaction(self.resources.mongo) as db_session:
            session = await AuthSession.get(
                PydanticObjectId(session_id), session=db_session
            )
            if session is None or session.user_id != owner.id:
                raise NotFound("Session not found")
            if session.revoked_at is None:
                await session.set(
                    {AuthSession.revoked_at: datetime.now(UTC)}, session=db_session
                )
                await record_audit(
                    self.audit,
                    action,
                    actor_id=owner.id,
                    target_type="session",
                    target_id=session_id,
                    session=db_session,
                )

    async def revoke_others(self, owner: User, current_id: PydanticObjectId) -> None:
        now = datetime.now(UTC)
        async with transaction(self.resources.mongo) as db_session:
            result = await AuthSession.find(
                {
                    "user_id": owner.id,
                    "_id": {"$ne": current_id},
                    "revoked_at": None,
                    "expires_at": {"$gt": now},
                }
            ).update({"$set": {"revoked_at": now}}, session=db_session)
            await record_audit(
                self.audit,
                "OTHER_SESSIONS_REVOKED",
                actor_id=owner.id,
                target_type="user",
                target_id=str(owner.id),
                metadata={"revoked_count": result.modified_count},
                session=db_session,
            )
