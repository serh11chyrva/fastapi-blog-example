from backend.articles.models import Article
from backend.audit.models import AuditEvent
from backend.auth.models import AuthIdentity, AuthSession
from backend.comments.models import ArticleComment, CommentLike, PostReply
from backend.comments.conversion import ReplyMapping
from backend.interactions.models import PublicationInteraction
from backend.posts.models import MicroPost
from backend.profiles.models import BadgeAssignment, BadgeDefinition, Follow, User
from backend.storage.models import ImageUpload, ObjectCleanup

DOCUMENT_MODELS = [
    ReplyMapping,
    User,
    BadgeDefinition,
    AuthIdentity,
    AuthSession,
    AuditEvent,
    Follow,
    MicroPost,
    Article,
    PublicationInteraction,
    PostReply,
    ArticleComment,
    CommentLike,
    ImageUpload,
    ObjectCleanup,
]

__all__ = ["DOCUMENT_MODELS", "BadgeAssignment"]
