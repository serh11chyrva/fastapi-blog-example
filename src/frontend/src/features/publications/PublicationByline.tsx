import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import type { ProfileCard, ReplyMetadata, RepostFeedItem } from "../../shared/api/types";
import { Icon } from "../../shared/ui/Icon";
import { PublicationStatus } from "./PublicationStatus";
import { RelativeTime } from "../../shared/ui/RelativeTime";
import { HashtagText } from "../../shared/text/HashtagText";

export function PublicationByline({ author, reply, repost, href, publishedAt, updatedAt, pinnedAt, archivedAt, children }: {
  author?: ProfileCard; reply?: ReplyMetadata | null; repost?: RepostFeedItem;
  pinnedAt?: string | null; archivedAt?: string | null;
  href: string; publishedAt: string; updatedAt?: string | null; children?: ReactNode;
}) {
  const replyHref = reply?.parent_id ? `/posts/${reply.parent_id}`
    : reply ? `${reply.kind === "article" ? "/articles" : "/posts"}/${reply.publication_id}` : "";
  const replyLabel = reply?.parent_id ? "Replied to a reply"
    : reply?.kind === "article" ? "Commented on an article" : "Replied to a post";
  return <div className="post-byline">
    {author && <>
      <span className="post-name"><HashtagText text={author.display_name} href={`/@${author.username}`} /></span>
      <span className="post-meta">@{author.username}</span>
    </>}
    {reply && <span className="post-activity">
      {author && <span aria-hidden="true">·</span>}
      <Icon name="comment" width={15} height={15} />
      <Link to={replyHref}>{replyLabel}</Link>
    </span>}
    {repost && <span className="post-activity">
      {(author || reply) && <span aria-hidden="true">·</span>}
      <Icon name="repost" width={15} height={15} />
      <span><HashtagText text={repost.reposted_by.display_name} href={`/@${repost.reposted_by.username}`} /></span>
      <span>reposted</span>
    </span>}
    <PublicationStatus pinnedAt={pinnedAt} archivedAt={archivedAt} />
    <span className="post-meta">
      {(author || reply || repost) && <span aria-hidden="true">· </span>}
      <Link to={href}>
        <RelativeTime publishedAt={publishedAt} updatedAt={updatedAt} repostedAt={repost?.published_at} pinnedAt={pinnedAt} archivedAt={archivedAt} />
      </Link>
    </span>
    {children}
  </div>;
}
