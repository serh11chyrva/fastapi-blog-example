from backend.audit.models import AuditEvent
from backend.auth.models import AuthIdentity, AuthSession
from backend.content.models import Article, MicroPost
from backend.profiles.models import BadgeAssignment, Follow, User

DOCUMENT_MODELS = [User, AuthIdentity, AuthSession, AuditEvent, Follow, MicroPost, Article]

__all__ = ["DOCUMENT_MODELS", "BadgeAssignment"]
