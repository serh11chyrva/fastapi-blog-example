import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { useApp } from "../../app/AuthProvider";
import { api, errorMessage } from "../../shared/api/client";
import type { FeedItem, OriginalFeedItem, RepostFeedItem, MicroPost, Article } from "../../shared/api/types";
import { Avatar } from "../../shared/ui/Avatar";
import { HighlightedReplies } from "../comments/HighlightedReplies";
import { Discussion } from "../comments/Discussion";
import { PublicationActions } from "../interactions/PublicationActions";
import { PreviewCard } from "../publications/PreviewCard";
import { PublicationComposer } from "../publications/PublicationComposer";
import { PublicationMenu } from "../publications/PublicationMenu";
import { PublicationByline } from "../publications/PublicationByline";
import { PostContent } from "./PostContent";
import { HashtagText } from "../../shared/text/HashtagText";
import { Collapsible } from "../../shared/ui/Collapsible";

export function FeedCard({ item, onChanged, showDiscussion = false, excerpt }: {
  item: FeedItem;
  onChanged: () => void;
  showDiscussion?: boolean;
  excerpt?: string | null;
}) {
  const repost = item.kind === "repost" ? item : undefined;
  const original = item.kind === "repost" ? item.post : item;
  return <article className="feed-post motion-enter">
    <OriginalCard key={original.id} item={original} repost={repost} onChanged={onChanged} showDiscussion={showDiscussion} excerpt={excerpt} />
  </article>;
}

function OriginalCard({ item: initialItem, repost, onChanged, showDiscussion, excerpt }: {
  item: OriginalFeedItem;
  repost?: RepostFeedItem;
  onChanged: () => void;
  showDiscussion: boolean;
  excerpt?: string | null;
}) {
  const { user } = useApp();
  const [item, setItem] = useState(initialItem);
  useEffect(() => { setItem(initialItem); }, [initialItem]);
  function reconcile(updated: Article | MicroPost) {
    setItem(updated.kind === "micro_post" ? { ...updated, published_at: updated.created_at }
      : { ...updated, published_at: updated.published_at ?? initialItem.published_at });
  }
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);
  const [editPost, setEditPost] = useState<MicroPost | null>(null);
  const [busy, setBusy] = useState(false);
  const [comments, setComments] = useState(showDiscussion);
  const [focusReply, setFocusReply] = useState(false);
  const menu = useRef<HTMLDetailsElement>(null);
  const [author, ...featured] = item.authors;
  const own = user?.id === item.owner_id;
  const readOnly = !!item.read_only || !!item.archived_at;
  const page = item.share_url ?? (item.kind === "micro_post" ? `/posts/${item.id}` : `/articles/${item.id}`);

  async function share() {
    try {
      await navigator.clipboard.writeText(new URL(page, window.location.origin).toString());
      setCopied(true);
    } catch (reason) { setError(errorMessage(reason)); }
  }

  async function deletePost() {
    if (busy || !window.confirm("Delete this post?")) return;
    setBusy(true); setError("");
    try { await api(`/posts/${item.id}`, { method: "DELETE" }); onChanged(); }
    catch (reason) { setError(errorMessage(reason)); }
    finally { setBusy(false); }
  }

  async function beginEdit() {
    if (busy) return;
    closeMenu(); setBusy(true); setError("");
    try { setEditPost(await api<MicroPost>(`/posts/${item.id}`)); }
    catch (reason) { setError(errorMessage(reason)); }
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
      <PublicationByline author={author} reply={item.reply} repost={repost} href={page}
        publishedAt={item.published_at} updatedAt={item.updated_at} pinnedAt={item.pinned_at} archivedAt={item.archived_at}>
        <PublicationMenu item={item} menuRef={menu} disabled={busy} readOnly={readOnly} onChanged={() => onChanged()} onReconciled={reconcile}>
          <Link to={page} onClick={closeMenu}>Open {item.kind === "micro_post" ? "post" : "article"}</Link>
          {own && item.kind === "micro_post" && <>
            <button type="button" disabled={busy} onClick={() => void beginEdit()}>Edit post</button>
            <button type="button" disabled={busy} onClick={() => { closeMenu(); void deletePost(); }}>Delete post</button>
          </>}
          {own && item.kind === "article" && <Link to={`/articles/${item.id}/edit`} onClick={closeMenu}>Edit article</Link>}
        </PublicationMenu>
      </PublicationByline>
      {featured.length > 0 && <div className="post-credits">With {featured.map((person, index) => <span key={person.id}>
        {index > 0 && ", "}<HashtagText text={person.display_name} href={`/@${person.username}`} />
      </span>)}</div>}
      {item.kind === "micro_post" ? <>
        {editPost ? <PublicationComposer post={editPost} label="Save changes"
          onCancel={() => setEditPost(null)} onSaved={() => { setEditPost(null); onChanged(); }} /> : <PostContent text={item.text} attachments={item.attachments} reply={item.reply} />}
      </> : <PreviewCard item={item} excerpt={excerpt} />}
      {!readOnly && <PublicationActions key={`actions:${item.kind}:${item.id}`} kind={item.kind} id={item.id}
        onComments={() => { setFocusReply(!comments); setComments(!comments); }}
        commentsOpen={comments} onShare={() => void share()} copied={copied}
        onChanged={(action) => { if (action === "repost") onChanged(); }} />}
      {readOnly && <button type="button" className="text-link" aria-expanded={comments}
        onClick={() => setComments(!comments)}>
        {comments ? "Hide discussion" : "View discussion"}</button>}
      {error && <p className="notice-error" role="alert">{error}</p>}
      {item.kind === "micro_post" && !readOnly && <Collapsible key="highlighted-replies" open={!comments}>
        <HighlightedReplies key={item.id} postId={item.id} />
      </Collapsible>}
      <Collapsible key="discussion" open={comments} animateInitial={!showDiscussion}>
        <Discussion key={`${item.kind}:${item.id}`} kind={item.kind} id={item.id} readOnly={readOnly}
          visible={comments} focusComposer={comments && focusReply} />
      </Collapsible>
    </div>
  </div>;
}
