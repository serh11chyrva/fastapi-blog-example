import { useRef, useState } from "react";
import { Link } from "react-router-dom";
import { useApp } from "../../app/AuthProvider";
import { api, errorMessage } from "../../shared/api/client";
import type { FeedItem, OriginalFeedItem, RepostFeedItem } from "../../shared/api/types";
import { Avatar } from "../../shared/ui/Avatar";
import { Icon } from "../../shared/ui/Icon";
import { RelativeTime } from "../../shared/ui/RelativeTime";
import { HighlightedReplies } from "../comments/HighlightedReplies";
import { Discussion } from "../comments/Discussion";
import { PublicationActions } from "../interactions/PublicationActions";
import { PreviewCard } from "../publications/PreviewCard";
import { PostContent } from "./PostContent";

export function FeedCard({ item, onChanged, showDiscussion = false }: {
  item: FeedItem;
  onChanged: () => void;
  showDiscussion?: boolean;
}) {
  const repost = item.kind === "repost" ? item : undefined;
  const original = item.kind === "repost" ? item.post : item;
  return <article className="feed-post">
    <OriginalCard key={original.id} item={original} repost={repost} onChanged={onChanged} showDiscussion={showDiscussion} />
  </article>;
}

function OriginalCard({ item, repost, onChanged, showDiscussion }: {
  item: OriginalFeedItem;
  repost?: RepostFeedItem;
  onChanged: () => void;
  showDiscussion: boolean;
}) {
  const { user } = useApp();
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);
  const [editing, setEditing] = useState(false);
  const [text, setText] = useState(item.kind === "micro_post" ? item.text : "");
  const [busy, setBusy] = useState(false);
  const [comments, setComments] = useState(showDiscussion);
  const menu = useRef<HTMLDetailsElement>(null);
  const [author, ...featured] = item.authors;
  const own = user?.id === item.owner_id;
  const page = item.share_url ?? (item.kind === "micro_post" ? `/posts/${item.id}` : `/articles/${item.id}`);

  async function share() {
    try {
      await navigator.clipboard.writeText(new URL(page, window.location.origin).toString());
      setCopied(true);
    } catch (reason) { setError(errorMessage(reason)); }
  }

  async function changePost(remove = false) {
    if (busy || (remove && !window.confirm("Delete this post?"))) return;
    setBusy(true);
    setError("");
    try {
      await api(`/posts/${item.id}`, { method: remove ? "DELETE" : "PATCH",
        ...(remove ? {} : { body: JSON.stringify({ text }) }) });
      setEditing(false);
      onChanged();
    } catch (reason) { setError(errorMessage(reason)); }
    finally { setBusy(false); }
  }

  function closeMenu() {
    menu.current?.removeAttribute("open");
  }

  return <div className="post-layout">
    {author && <Link to={`/@${author.username}`} className="post-avatar" aria-label={`${author.display_name}'s profile`}>
      <Avatar name={author.display_name} src={author.avatars.original} size="sm" />
    </Link>}
    <div className="post-content">
      <div className="post-byline">
        {author && <Link to={`/@${author.username}`} className="post-name">{author.display_name}</Link>}
        {author && <span className="post-meta">@{author.username}</span>}
        {repost && <span className="post-activity">
          {author && <span aria-hidden="true">·</span>}
          <Icon name="repost" width={15} height={15} />
          <Link to={`/@${repost.reposted_by.username}`}>{repost.reposted_by.display_name}</Link>
          <span>reposted</span>
        </span>}
        <span className="post-meta">
          {(author || repost) && <span aria-hidden="true">· </span>}
          <Link to={page}>
            <RelativeTime publishedAt={item.published_at} updatedAt={item.updated_at} repostedAt={repost?.published_at} />
          </Link>
        </span>
        <details className="post-menu" ref={menu}>
          <summary className="icon-button" aria-label="More publication actions" title="More actions"><Icon name="more" /></summary>
          <div className="post-menu-list">
            <Link to={page} onClick={closeMenu}>Open {item.kind === "micro_post" ? "post" : "article"}</Link>
            {own && item.kind === "micro_post" && <>
              <button type="button" disabled={busy} onClick={() => { setText(item.text); setEditing(true); closeMenu(); }}>Edit post</button>
              <button type="button" disabled={busy} onClick={() => { closeMenu(); void changePost(true); }}>Delete post</button>
            </>}
            {own && item.kind === "article" && <Link to={`/articles/${item.id}/edit`} onClick={closeMenu}>Edit article</Link>}
          </div>
        </details>
      </div>
      {featured.length > 0 && <div className="post-credits">With {featured.map((person, index) => <span key={person.id}>
        {index > 0 && ", "}<Link to={`/@${person.username}`}>{person.display_name}</Link>
      </span>)}</div>}
      {item.kind === "micro_post" ? <>
        {editing ? <form className="post-edit" onSubmit={(event) => { event.preventDefault(); void changePost(); }}>
          <label className="form-label">Edit post<textarea className="field" maxLength={280}
            value={text} disabled={busy} onChange={(event) => setText(event.target.value)} /></label>
          <button className="button-primary" disabled={busy || !text.trim()}>Save</button>{" "}
          <button type="button" className="button-quiet" disabled={busy} onClick={() => setEditing(false)}>Cancel</button>
        </form> : <PostContent text={item.text} attachments={item.attachments} reply={item.reply} />}
      </> : <PreviewCard item={item} />}
      <PublicationActions key={`${item.kind}:${item.id}`} kind={item.kind} id={item.id}
        onComments={() => setComments((value) => !value)} commentsOpen={comments} onShare={() => void share()} copied={copied}
        onChanged={(action) => { if (action === "repost") onChanged(); }} />
      {error && <p className="notice-error" role="alert">{error}</p>}
      {item.kind === "micro_post" && !comments && <HighlightedReplies postId={item.id} openDiscussion={() => setComments(true)} />}
      {comments && <Discussion key={`${item.kind}:${item.id}`} kind={item.kind} id={item.id} />}
    </div>
  </div>;
}
