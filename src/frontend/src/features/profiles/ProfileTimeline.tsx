import { Link } from "react-router-dom";
import type { ProfileActivity } from "../../shared/api/types";
import { useCursorList } from "../../shared/hooks/useCursorList";
import { Avatar } from "../../shared/ui/Avatar";
import { Icon } from "../../shared/ui/Icon";
import { RelativeTime } from "../../shared/ui/RelativeTime";
import { FeedCard } from "../feed/FeedCard";
import { PostText } from "../feed/PostText";
import { PreviewCard } from "../publications/PreviewCard";

function activityKey(item: ProfileActivity) {
  return `${item.kind}:${item.id}`;
}

export function ProfileTimeline({ username, onChanged }: { username: string; onChanged: () => void }) {
  const list = useCursorList<ProfileActivity>(`/users/${encodeURIComponent(username)}/timeline`, activityKey);
  return <div className="feed-list">
    {list.items.map((item) => item.kind === "article_comment"
      ? <article className="feed-post" key={activityKey(item)}>
          <div className="post-layout">
            <Link className="post-avatar" to={`/@${item.author.username}`}>
              <Avatar name={item.author.display_name} src={item.author.avatars.original} size="sm" />
            </Link>
            <div className="post-content">
              <div className="post-byline">
                <Link className="post-name" to={`/@${item.author.username}`}>{item.author.display_name}</Link>
                <span className="post-meta">@{item.author.username}</span>
                <span className="post-activity">
                  <span aria-hidden="true">·</span>
                  <Icon name="comment" width={15} height={15} />
                  <span>commented on an article</span>
                </span>
                <span className="post-meta">
                  <span aria-hidden="true">· </span>
                  <Link to={`${item.article.share_url}#comment-${item.id}`}>
                    <RelativeTime publishedAt={item.created_at} updatedAt={item.updated_at} />
                  </Link>
                </span>
              </div>
              <PostText text={item.text} />
              <PreviewCard item={item.article} />
              <Link className="comment-jump" to={`${item.article.share_url}#comment-${item.id}`}>
                <Icon name="comment" width={15} height={15} /> Open comment
              </Link>
            </div>
          </div>
        </article>
      : <FeedCard key={activityKey(item)} item={item} onChanged={onChanged} />)}
    {list.loading && <p className="list-status" role="status">Loading activity…</p>}
    {list.error && <p className="notice-error" role="alert">{list.error}{" "}
      <button className="text-link" onClick={list.cursor ? () => void list.loadMore() : list.refresh}>Retry</button>
    </p>}
    {!list.loading && !list.error && !list.items.length && !list.cursor && <p className="list-status">No public activity yet.</p>}
    {list.cursor && <button className="list-more" disabled={list.loading} onClick={() => void list.loadMore()}>Load more</button>}
  </div>;
}
