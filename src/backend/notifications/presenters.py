"""Batch current public actors and targets without persisting social content snapshots."""

from backend.articles.models import Article
from backend.notifications.models import NotificationGroup, NotificationTarget
from backend.notifications.schemas import (
    LoginNotification, LoginNotificationDetails, NotificationItem, NotificationTargetResponse, SocialNotification,
)
from backend.posts.models import MicroPost
from backend.posts.visibility import visible_post_stages
from backend.profiles.presenters import user_card
from backend.profiles.repository import ProfileRepository


def target_response(
    target: NotificationTarget, publication: MicroPost | Article | None,
) -> NotificationTargetResponse:
    """Build a reading destination only from a currently public publication.

    :param target: Stored publication reference; contains no cached text or title.
    :param publication: Currently public publication, or None when any visibility dependency is unavailable.
    :return: A current plain-text preview or a content-free placeholder without a destination.
    """
    if publication is None:
        return NotificationTargetResponse(
            kind=target.kind, id=str(target.id), available=False, label="publication", url=None, preview=None,
        )
    if isinstance(publication, Article):
        label = "article"
        preview = publication.title
        url = f"/articles/{publication.id}"
    else:
        label = "comment" if publication.reply is not None else "post"
        preview = publication.text or f"{label.capitalize()} with attachments"
        url = f"/posts/{publication.id}"
    return NotificationTargetResponse(
        kind=target.kind, id=str(target.id), available=True, label=label,
        url=url, preview=" ".join(preview.split())[:240],
    )


async def notification_items(groups: list[NotificationGroup]) -> list[NotificationItem]:
    """Hydrate a bounded inbox page using batched actor, article, and visibility-aware post reads.

    :param groups: Recipient-owned page of inbox rows, already in presentation order.
    :return: Typed rows with live public profiles and previews, preserving unavailable rows and counts.
    """
    actor_ids = list({key for group in groups for key in group.actor_ids})
    actors = {user.id: user_card(user) for user in await ProfileRepository.users_by_ids(actor_ids)} if actor_ids else {}
    targets = [group.target for group in groups if group.target is not None]
    post_ids = list({target.id for target in targets if target.kind == "micro_post"})
    article_ids = list({target.id for target in targets if target.kind == "article"})
    publications = {}
    if post_ids:
        rows = await MicroPost.aggregate([
            {"$match": {"_id": {"$in": post_ids}, "deleted_at": None}}, *visible_post_stages(),
        ]).to_list()
        publications.update({("micro_post", row["_id"]): MicroPost.model_validate(row) for row in rows})
    if article_ids:
        articles = await Article.find({
            "_id": {"$in": article_ids}, "deleted_at": None, "archived_at": None,
            "status": "published", "published_at": {"$ne": None},
        }).to_list()
        publications.update({("article", article.id): article for article in articles})

    items = []
    for group in groups:
        common = dict(
            id=str(group.id), version=group.latest_sequence, is_read=group.is_read, last_event_at=group.last_event_at,
        )
        if group.kind == "login":
            if group.login is None:
                raise ValueError("Login notifications require readable login details")
            items.append(LoginNotification(
                **common, kind="login", login=LoginNotificationDetails(**group.login.model_dump()),
            ))
        else:
            if group.target is None:
                raise ValueError("Social notifications require a publication target")
            items.append(SocialNotification(
                **common, kind=group.kind, event_count=group.event_count,
                actors=[actors[key] for key in group.actor_ids if key in actors],
                target=target_response(group.target, publications.get((group.target.kind, group.target.id))),
            ))
    return items
