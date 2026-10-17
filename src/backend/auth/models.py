from datetime import datetime

from beanie import Document, PydanticObjectId
from pymongo import ASCENDING, IndexModel

from backend.auth.client import ClientType


class AuthIdentity(Document):
    user_id: PydanticObjectId
    provider: str = "password"
    subject: str
    password_hash: str | None = None
    created_at: datetime

    class Settings:
        name = "auth_identities"
        indexes = [
            IndexModel([("provider", ASCENDING), ("subject", ASCENDING)], unique=True, name="auth_identity_provider_subject_unique"),
            IndexModel([("user_id", ASCENDING), ("provider", ASCENDING)], name="auth_identity_user_provider"),
        ]


class AuthSession(Document):
    user_id: PydanticObjectId
    token_hash: str
    created_at: datetime
    last_seen_at: datetime
    expires_at: datetime
    ip_address: str | None = None
    user_agent: str | None = None
    client_type: ClientType = ClientType.WEB
    device_name: str | None = None
    revoked_at: datetime | None = None

    class Settings:
        name = "auth_sessions"
        indexes = [
            IndexModel([("token_hash", ASCENDING)], unique=True, name="sessions_token_hash_unique"),
            IndexModel([("user_id", ASCENDING), ("revoked_at", ASCENDING), ("expires_at", ASCENDING)], name="sessions_user_active"),
        ]
