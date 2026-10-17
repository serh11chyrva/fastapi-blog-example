"""Account registration and login workflows; HTTP cookie handling stays in the router."""

from datetime import UTC, datetime

from beanie import PydanticObjectId
from pymongo.errors import DuplicateKeyError

from backend.audit.context import AuditContext
from backend.audit.service import record_audit
from backend.auth.models import AuthIdentity
from backend.auth.schemas import LoginRequest, RegisterRequest
from backend.auth.security import hash_password_async
from backend.auth.service import AuthService, PasswordRejected
from backend.auth.sessions import SessionService, prepare_session
from backend.core.errors import ApplicationError, Conflict
from backend.core.resources import AppResources
from backend.core.transactions import transaction
from backend.profiles.models import User


class InvalidCredentials(ApplicationError):
    status_code = 401


class AccountService:
    def __init__(self, resources: AppResources, audit: AuditContext) -> None:
        self.resources = resources
        self.audit = audit

    async def register(self, payload: RegisterRequest) -> tuple[User, str]:
        password_hash = await hash_password_async(payload.password)
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
            password_hash=password_hash,
            created_at=now,
        )
        token, session = prepare_session(
            user,
            self.audit,
            now,
            client_type=payload.client_type,
            device_name=payload.device_name,
        )
        try:
            async with transaction(self.resources.mongo) as db_session:
                await user.insert(session=db_session)
                await identity.insert(session=db_session)
                await session.insert(session=db_session)
                await record_audit(
                    self.audit,
                    "USER_REGISTERED",
                    actor_id=user.id,
                    target_type="user",
                    target_id=str(user.id),
                    session=db_session,
                )
        except DuplicateKeyError as exc:
            raise Conflict("Email or username is already in use") from exc
        return user, token

    async def login(self, payload: LoginRequest) -> tuple[User, str]:
        authentication = await AuthService().authenticate_password(
            payload.identifier, payload.password
        )
        if isinstance(authentication, PasswordRejected):
            user = authentication.user
            identifier = payload.identifier.strip()
            await record_audit(
                self.audit,
                "LOGIN_FAILED",
                actor_id=user.id if user else None,
                target_type="user" if user else None,
                target_id=str(user.id) if user else None,
                metadata={
                    "identifier_type": "email"
                    if "@" in identifier and not identifier.startswith("@")
                    else "username"
                },
            )
            raise InvalidCredentials("Invalid username/email or password")
        token = await SessionService(self.resources, self.audit).create(
            authentication.user,
            authentication.identity if authentication.needs_rehash else None,
            client_type=payload.client_type,
            device_name=payload.device_name,
        )
        return authentication.user, token
