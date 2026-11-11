import { Link } from "react-router-dom";
import type { MicroPost } from "../../shared/api/types";
import { Avatar } from "../../shared/ui/Avatar";
import { RelativeTime } from "../../shared/ui/RelativeTime";
import { PostContent } from "../feed/PostContent";
import { PublicationActions } from "../interactions/PublicationActions";

export function ReplyPublication({ post, onComments, commentsOpen, onChanged }: {
  post: MicroPost; onComments: () => void; commentsOpen?: boolean; onChanged?: () => void;
}) {
  const author = post.authors[0];
  return <div className="post-layout reply-publication">
    <Link className="post-avatar" to={`/@${author.username}`} aria-label={`${author.display_name}'s profile`}>
      <Avatar name={author.display_name} src={author.avatars.original} size="sm" />
    </Link>
    <div className="post-content">
      <div className="post-byline">
        <Link className="post-name" to={`/@${author.username}`}>{author.display_name}</Link>
        <span className="post-meta">@{author.username}</span>
        <Link className="post-meta" to={post.share_url ?? `/posts/${post.id}`}>
          <RelativeTime publishedAt={post.created_at} updatedAt={post.updated_at} />
        </Link>
      </div>
      <PostContent text={post.text} attachments={post.attachments} reply={post.reply} context={false} />
      <PublicationActions kind="micro_post" id={post.id} onComments={onComments}
        commentsOpen={commentsOpen} onChanged={onChanged} />
    </div>
  </div>;
}
