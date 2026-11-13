import { Link } from "react-router-dom";
import type { ReactNode } from "react";
import type { InteractionAction, MicroPost } from "../../shared/api/types";
import { Avatar } from "../../shared/ui/Avatar";
import { PublicationByline } from "../publications/PublicationByline";
import { PostContent } from "../feed/PostContent";
import { PublicationActions } from "../interactions/PublicationActions";

export function ReplyPublication({ post, onChanged, menu, readOnly = false }: {
  post: MicroPost; readOnly?: boolean;
  onChanged?: (action: InteractionAction, enabled: boolean) => void; menu?: ReactNode;
}) {
  const author = post.authors[0];
  return <div className="post-layout reply-publication">
    <Link className="post-avatar" to={`/@${author.username}`} aria-label={`${author.display_name}'s profile`}>
      <Avatar name={author.display_name} src={author.avatars.original} size="sm" />
    </Link>
    <div className="post-content">
      <PublicationByline author={author} reply={post.reply} href={post.share_url ?? `/posts/${post.id}`}
        publishedAt={post.created_at} updatedAt={post.updated_at} pinnedAt={post.pinned_at} archivedAt={post.archived_at}>{menu}</PublicationByline>
      <PostContent text={post.text} attachments={post.attachments} reply={post.reply} context={false} />
      {!readOnly && <PublicationActions kind="micro_post" id={post.id}
        commentsHref={`${post.share_url ?? `/posts/${post.id}`}#replies`} onChanged={onChanged} />}
      {readOnly && <Link className="text-link" to={`/posts/${post.id}#replies`}>View replies</Link>}
    </div>
  </div>;
}
