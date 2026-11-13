import { Link } from "react-router-dom";
import type { ReplyTombstone } from "../../shared/api/types";
import { RelativeTime } from "../../shared/ui/RelativeTime";

export function TombstoneCard({ post, selected = false }: { post: ReplyTombstone; selected?: boolean }) {
  return <article className="feed-post deleted-reply">
    <p className="post-name">Deleted reply</p>
    <RelativeTime publishedAt={post.created_at} updatedAt={post.updated_at} />
    <p className="comment-copy">This reply was deleted. Its place in the conversation is preserved.</p>
    {!selected && <Link className="text-link" to={`/posts/${post.id}#replies`}>View replies</Link>}
  </article>;
}
