"""Repeatable follow, reaction, session, and discussion fixtures."""

from datetime import datetime, timedelta

from backend.articles.models import Article
from backend.auth.client import ClientType
from backend.auth.sessions import prepare_session
from backend.comments.models import ArticleComment, CommentLike, PostReply
from backend.comments.schemas import CommentText
from backend.comments.service import CommentService
from backend.core.resources import AppResources
from backend.demo.common import DEMO_AUDIT, demo_id, insert_fixture
from backend.interactions.models import PublicationInteraction
from backend.posts.models import MicroPost
from backend.profiles.models import Follow, User
from backend.publications.access import PublicationKind


async def seed_activity(
    resources: AppResources, users: dict[str, User], posts: dict[str, MicroPost],
    articles: dict[str, Article], now: datetime,
) -> None:
    """Add follow graphs, likes, private saves, reposts, and illustrative active sessions.

    :param resources: Transactional database and cache infrastructure.
    :param users: Demo users indexed by username.
    :param posts: Existing stable post fixtures, including any owner-deleted examples.
    :param articles: Existing stable article fixtures, including any owner-edited states.
    :param now: Timezone-aware seed timestamp.
    :return: None.
    """
    pairs = [
        ("alice", "ben"), ("alice", "casey"), ("alice", "dana"), ("ben", "alice"), ("ben", "farah"),
        ("casey", "alice"), ("casey", "ben"), ("dana", "elena"), ("elena", "casey"),
        ("elena", "farah"), ("farah", "alice"), ("farah", "dana"),
    ]
    for index, (follower, followee) in enumerate(pairs):
        if await Follow.find_one(
            Follow.follower_id == users[follower].id, Follow.followee_id == users[followee].id,
        ) is None:
            await insert_fixture(
                resources,
                Follow(
                    id=demo_id("follow", index), follower_id=users[follower].id,
                    followee_id=users[followee].id, created_at=now - timedelta(days=4),
                ),
                users[follower].id, "follow",
            )

    publications = [*posts.values(), *articles.values()]
    participants = ["alice", "ben", "casey", "dana", "elena", "farah"]

    for index, publication in enumerate(publications):
        if publication.deleted_at is not None or (
            isinstance(publication, Article) and publication.status != "published"
        ):
            continue
        kind = "micro_post" if isinstance(publication, MicroPost) else "article"
        actions = [(participants[(index + 1) % 6], "like"), (participants[(index + 2) % 6], "like")]

        if index < 24 or kind == "article":
            actions.append(("alice", "save"))
        if index < 8:
            actions.append(("ben", "save"))
        if kind == "micro_post" and index < 22:
            actions.append(("alice", "repost"))
        if kind == "micro_post" and index % 5 == 0:
            actions.append(("casey", "repost"))

        for username, action in actions:
            owner = users[username]
            if await PublicationInteraction.find_one(
                PublicationInteraction.publication_kind == kind,
                PublicationInteraction.publication_id == publication.id,
                PublicationInteraction.user_id == owner.id,
                PublicationInteraction.action == action,
            ) is not None:
                continue

            edge = PublicationInteraction(
                id=demo_id(f"interaction:{username}:{action}:{publication.id}"), publication_kind=kind,
                publication_id=publication.id, user_id=owner.id, action=action,
                created_at=now - timedelta(minutes=5 + index),
            )
            await insert_fixture(resources, edge, owner.id, "interaction")

    for username in ["alice", "ben", "casey"]:
        for number, (client_type, device_name) in enumerate([
            (ClientType.WEB, None),
            (ClientType.MOBILE, "Demo phone"),
            (ClientType.DESKTOP, "Demo laptop"),
        ]):
            _, auth_session = prepare_session(
                users[username], DEMO_AUDIT, now - timedelta(hours=number + 1),
                client_type=client_type, device_name=device_name,
            )
            auth_session.id = demo_id(f"session:{username}", number)
            auth_session.user_agent = (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
                if number == 0 else "FastAPIBlogExampleDemo/3.0"
            )
            await insert_fixture(resources, auth_session, users[username].id, "session")


async def seed_discussions(
    resources: AppResources, users: dict[str, User], posts: dict[str, MicroPost],
    articles: dict[str, Article],
) -> None:
    """Populate existing discussion examples, then add ranked conversations to the new fixtures.

    :param resources: Infrastructure used to commit comments and audit events atomically.
    :param users: Demo comment authors indexed by username.
    :param posts: Stable post fixtures; deleted publications are left untouched.
    :param articles: Stable article fixtures; private or deleted publications receive no new comments.
    :return: None.
    """
    names = ["alice", "ben", "casey", "dana", "elena", "farah"]
    post = posts["note-00"]
    article = articles["reading-room"]

    observations = [
        "A concrete example makes this much easier to follow.",
        "I tried this approach in my notebook and would happily do it again.",
        "The most useful part for me was leaving a little room for revision.",
        "Which small change made the biggest difference for you?",
    ]
    if post.deleted_at is None:
        for index in range(26):
            author = users[names[index % len(names)]]
            root_id = demo_id("discussion-roots", index)
            created_at = post.created_at + timedelta(seconds=(index + 1) * 30)
            text = CommentText(text=f"Reading circle {index + 1:02d}: {observations[index % 4]}").text
            await insert_fixture(
                resources,
                PostReply(
                    id=root_id, post_id=post.id, author_id=author.id, root_id=root_id,
                    text="" if index == 1 else text, created_at=created_at,
                    updated_at=created_at + timedelta(minutes=2) if index in {1, 3} else created_at,
                    deleted_at=created_at + timedelta(minutes=2) if index == 1 else None,
                ),
                author.id, "post_reply",
            )

        parent_id = demo_id("discussion-roots", 0)
        for depth in range(1, 7):
            author = users[names[depth % len(names)]]
            reply_id = demo_id("deep-replies", depth)
            reply = PostReply(
                id=reply_id, post_id=post.id, author_id=author.id,
                root_id=demo_id("discussion-roots", 0), parent_id=parent_id, depth=depth,
                text=CommentText(text=f"Thread level {depth}: one more useful detail for this conversation.").text,
                created_at=post.created_at + timedelta(minutes=20, seconds=depth * 30),
                updated_at=post.created_at + timedelta(minutes=20, seconds=depth * 30),
            )
            await insert_fixture(resources, reply, author.id, "post_reply")
            parent_id = reply_id

        for index in range(2):
            author = users[names[index + 2]]
            await insert_fixture(
                resources,
                PostReply(
                    id=demo_id("preserved-branch", index), post_id=post.id, author_id=author.id,
                    parent_id=demo_id("discussion-roots", 1), root_id=demo_id("discussion-roots", 1),
                    depth=1, text="This reply remains readable after its parent comment was deleted.",
                    created_at=post.created_at + timedelta(minutes=25, seconds=index * 30),
                    updated_at=post.created_at + timedelta(minutes=25, seconds=index * 30),
                ),
                author.id, "post_reply",
            )

    if article.status == "published" and article.deleted_at is None:
        for index in range(26):
            author = users[names[index % len(names)]]
            created_at = (article.published_at or article.created_at) + timedelta(seconds=(index + 1) * 20)
            text = CommentText(
                text=f"Reader note {index + 1:02d}: a little structure makes a long article much easier to revisit."
            ).text
            await insert_fixture(
                resources,
                ArticleComment(
                    id=demo_id("article-comments", index), article_id=article.id, author_id=author.id,
                    text="" if index == 4 else text, created_at=created_at,
                    updated_at=created_at + timedelta(minutes=3) if index in {3, 4} else created_at,
                    deleted_at=created_at + timedelta(minutes=3) if index == 4 else None,
                ),
                author.id, "article_comment",
            )

    await seed_ranked_discussions(resources, users, posts, articles)


async def seed_ranked_discussions(
    resources: AppResources, users: dict[str, User], posts: dict[str, MicroPost], articles: dict[str, Article],
) -> None:
    """Add ranked replies and comments whose latest entry differs from the most liked.

    :param resources: Infrastructure used by fixture writes and the real reaction service.
    :param users: Demo accounts indexed by username.
    :param posts: Stable public post fixtures and their current visibility.
    :param articles: Stable article fixtures and their current visibility.
    :return: None.
    """
    quoted = posts["note-36"]
    workbench = articles["publishing-workbench"]
    if quoted.deleted_at is None:
        for index, (username, text) in enumerate([
            ("ben", "Linking the original keeps the useful context within reach."),
            ("casey", "This is the kind of small example I can try between bigger tasks."),
        ]):
            author = users[username]
            reply_id = demo_id("quote-replies", index)
            created_at = quoted.created_at + timedelta(seconds=(index + 1) * 30)
            await insert_fixture(
                resources,
                PostReply(
                    id=reply_id, post_id=quoted.id, author_id=author.id, root_id=reply_id,
                    text=text, created_at=created_at, updated_at=created_at,
                ),
                author.id, "post_reply",
            )

    if workbench.status == "published" and workbench.deleted_at is None:
        for index, (username, text) in enumerate([
            ("casey", "I like how the checklist ends with a question. It gives readers a way into the draft."),
            ("dana", "The linked reference is enough to try this idea without losing the thread of the article."),
            ("ben", "I saved the example to revisit the next time a draft feels too large to finish."),
            ("farah", "The Python block makes the idea concrete. A tiny example travels further than a long rule."),
            ("elena", "The section links make it easy to come back to the part I wanted to reread."),
            ("alice", "I added the short example after rereading the first draft. Thanks for the suggestions."),
        ]):
            author = users[username]
            created_at = (workbench.published_at or workbench.created_at) + timedelta(minutes=6 + index)
            await insert_fixture(
                resources,
                ArticleComment(
                    id=demo_id("workbench-comments", index), article_id=workbench.id, author_id=author.id,
                    text=text, created_at=created_at, updated_at=created_at,
                ),
                author.id, "article_comment",
            )

    examples: list[tuple[PublicationKind, MicroPost | Article, str, int, tuple[str, ...]]] = [
        ("micro_post", posts["note-00"], "discussion-roots", 0, ("ben", "casey", "dana", "farah")),
        ("micro_post", posts["note-00"], "discussion-roots", 3, ("alice", "elena")),
        ("micro_post", quoted, "quote-replies", 0, ("alice", "casey", "dana")),
        ("micro_post", quoted, "quote-replies", 1, ("elena",)),
        ("article", articles["reading-room"], "article-comments", 0, ("ben", "casey", "dana", "elena")),
        ("article", articles["reading-room"], "article-comments", 3, ("alice", "farah")),
        ("article", workbench, "workbench-comments", 0, ("alice", "ben", "dana", "elena", "farah")),
        ("article", workbench, "workbench-comments", 1, ("alice", "casey")),
        ("article", workbench, "workbench-comments", 3, ("ben", "elena")),
    ]
    comments = CommentService(resources, DEMO_AUDIT)
    for kind, publication, namespace, index, readers in examples:
        if publication.deleted_at is not None or (isinstance(publication, Article) and publication.status != "published"):
            continue

        comment_id = demo_id(namespace, index)
        entry = await comments.repository.get(kind, publication.id, comment_id)
        if entry is None or entry.deleted_at is not None:
            continue

        liked = await CommentLike.find({"kind": kind, "comment_id": comment_id}).to_list()
        likers = {reaction.user_id for reaction in liked}
        for username in readers:
            reader = users[username]
            if reader.id not in likers:
                await comments.set_like(kind, str(publication.id), str(comment_id), reader, enabled=True)
