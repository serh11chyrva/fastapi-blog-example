import { useEffect, useRef, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { useApp } from "../../app/AuthProvider";
import { api, errorMessage } from "../../shared/api/client";
import type { DiscussionComment, PublicationKind } from "../../shared/api/types";
import { useCursorList } from "../../shared/hooks/useCursorList";
import { Avatar } from "../../shared/ui/Avatar";
import { PublicationComposer } from "../publications/PublicationComposer";
import { ReplyPublication } from "./ReplyPublication";
import { RelativeTime } from "../../shared/ui/RelativeTime";
import { notifyInteractionChange, publicationPath } from "../interactions/events";

export function Discussion({ kind, id, deepLink = false }: { kind: PublicationKind; id: string; deepLink?: boolean }) {
  const { user } = useApp();
  const location = useLocation();
  const commentId = deepLink && kind === "article" ? /^#comment-([0-9a-f]{24})$/i.exec(location.hash)?.[1] : undefined;
  return <section className="discussion" aria-label={kind === "micro_post" ? "Post replies" : "Article comments"}>
    {!user && <p className="discussion-signin"><Link className="text-link" to="/login"
      state={{ from: location.pathname + location.search + location.hash }}>Sign in</Link> to join the conversation.</p>}
    <CommentList key={`${kind}:${id}:${user?.id ?? "anonymous"}`} kind={kind} id={id} commentId={commentId} />
  </section>;
}

function CommentForm({ path, parentId, label, onCreated, onCancel }: {
  path: string; parentId?: string; label: string;
  onCreated: (comment: DiscussionComment) => void; onCancel?: () => void;
}) {
  return <PublicationComposer replyPath={path} parentId={parentId} label={label}
    onCancel={onCancel} onSaved={(saved) => onCreated(saved as DiscussionComment)} />;
}

function CommentList({ kind, id, parentId, newComments, onRecentUpdate, commentId }: {
  kind: PublicationKind; id: string; parentId?: string; newComments?: DiscussionComment[];
  onRecentUpdate?: (comment: DiscussionComment) => void;
  commentId?: string;
}) {
  const { user } = useApp();
  const base = `${publicationPath(kind, id)}/${kind === "micro_post" ? "replies" : "comments"}`;
  const [sort, setSort] = useState<"most_liked" | "newest">("most_liked");
  const [recent, setRecent] = useState<DiscussionComment[]>([]);
  const [linked, setLinked] = useState<DiscussionComment | null>(null);
  const [linkError, setLinkError] = useState("");
  const path = parentId ? `${base}?parent_id=${encodeURIComponent(parentId)}`
    : kind === "article" ? `${base}?sort=${sort}` : base;
  const list = useCursorList<DiscussionComment>(path);
  const listed = list.items.some((item) => item.id === commentId) || recent.some((item) => item.id === commentId);

  useEffect(() => {
    setLinked(null);
    setLinkError("");
  }, [base, commentId]);

  useEffect(() => {
    if (!commentId || listed || list.loading || linked?.id === commentId) return;
    const controller = new AbortController();
    api<DiscussionComment>(`${base}/${encodeURIComponent(commentId)}`, { signal: controller.signal })
      .then((value) => { if (!controller.signal.aborted) setLinked(value); })
      .catch((reason: unknown) => { if (!controller.signal.aborted) setLinkError(errorMessage(reason)); });
    return () => controller.abort();
  }, [base, commentId, listed, list.loading, linked?.id]);

  const linkReady = listed || linked?.id === commentId;
  useEffect(() => {
    if (commentId && linkReady) document.getElementById(`comment-${commentId}`)?.scrollIntoView({ block: "center" });
  }, [commentId, linkReady]);
  useEffect(() => {
    if (newComments?.length) {
      setRecent((items) => [...items, ...newComments.filter((comment) => !items.some((item) => item.id === comment.id))]);
    }
  }, [newComments]);
  const visibleRecent = recent.filter((comment) => !list.items.some((item) => item.id === comment.id));
  function update(updated: DiscussionComment) {
    const apply = (items: DiscussionComment[]) => items.flatMap((item) => item.id !== updated.id ? [item]
      : [updated]);
    list.setItems(apply);
    setRecent(apply);
    setLinked((item) => item?.id === updated.id ? updated : item);
    onRecentUpdate?.(updated);
  }
  function created(comment: DiscussionComment) {
    setRecent((items) => [...items, comment]);
    notifyInteractionChange({ kind, id });
  }
  function renderComment(comment: DiscussionComment) {
    return <CommentItem key={comment.id} comment={comment} kind={kind} publicationId={id}
      base={base} onUpdate={update}
      anchor={comment.id === commentId} onReaction={kind === "article" && sort === "most_liked" ? list.refresh : undefined} />;
  }
  return <div>
    {!parentId && <div className="discussion-header">
      <h2>{kind === "article" ? "The conversation" : "Replies"}</h2>
      {kind === "article" && <select className="discussion-sort" aria-label="Sort comments" value={sort} onChange={(event) =>
        setSort(event.target.value === "newest" ? "newest" : "most_liked")}>
        <option value="most_liked">Most liked</option><option value="newest">Newest first</option>
      </select>}
    </div>}
    {user && !parentId && <CommentForm path={base} label={kind === "micro_post" ? "Your reply" : "Your comment"}
      onCreated={created} />}
    {commentId && linked?.id === commentId && !listed && <div className="my-4">
      <p className="text-xs font-semibold text-neutral-600">Linked comment</p>
      {renderComment(linked)}
    </div>}
    {linkError && <p className="notice-error" role="alert">{linkError}</p>}
    {visibleRecent.length > 0 && <div className="my-4 space-y-4">
      <p className="text-sm text-neutral-500" role="status">Just sent{list.cursor && " · Load more to continue the earlier conversation."}</p>
      {visibleRecent.map(renderComment)}
    </div>}
    <div className="space-y-4">
      {list.items.map(renderComment)}
    </div>
    {list.loading && <p role="status" className="py-3 text-sm text-neutral-500">Loading conversation…</p>}
    {list.error && <p role="alert" className="notice-error mt-3">{list.error}{" "}
      <button className="underline" onClick={list.cursor ? () => void list.loadMore() : list.refresh}>Retry</button>
    </p>}
    {!list.loading && !list.error && !list.items.length && !visibleRecent.length && <p className="py-3 text-sm text-neutral-500">No {parentId ? "replies" : kind === "micro_post" ? "replies yet. Start the conversation." : "comments yet. Be the first to comment."}</p>}
    {list.cursor && <button className="button-secondary mt-4" disabled={list.loading} onClick={() => void list.loadMore()}>Load more</button>}
    <button className="button-quiet mt-3 text-xs" disabled={list.loading} onClick={list.refresh}>Refresh conversation</button>
  </div>;
}

function CommentItem({ comment, kind, publicationId, base, onUpdate, onReaction, anchor }: {
  comment: DiscussionComment;
  kind: PublicationKind;
  publicationId: string;
  base: string;
  onUpdate: (comment: DiscussionComment) => void;
  onReaction?: () => void;
  anchor: boolean;
}) {
  const { user } = useApp();
  const [editing, setEditing] = useState(false);
  const [replying, setReplying] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const [recentReplies, setRecentReplies] = useState<DiscussionComment[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const pending = useRef(false);
  const active = useRef(true);
  useEffect(() => {
    active.current = true;
    return () => { active.current = false; };
  }, []);
  const thread = comment;
  const own = !!user && user.id === comment.author?.id && !comment.deleted;
  async function remove() {
    if (pending.current || !window.confirm("Delete your reply? Its children will remain available.")) return;
    pending.current = true; setBusy(true); setError("");
    try {
      await api(`${base}/${comment.id}`, { method: "DELETE" });
      if (!active.current) return;
      onUpdate({ ...comment, deleted: true, text: null, author: null, publication: null,
        likes_count: 0, liked: false, updated_at: new Date().toISOString() });
      notifyInteractionChange({ kind, id: publicationId });
    } catch (reason) { if (active.current) setError(errorMessage(reason)); }
    finally { pending.current = false; if (active.current) setBusy(false); }
  }

  async function reload() {
    if (pending.current) return;
    pending.current = true;
    setBusy(true);
    try {
      const updated = await api<DiscussionComment>(`${base}/${comment.id}`);
      if (!active.current) return;
      onUpdate(updated);
      setError("");
      notifyInteractionChange({ kind, id: publicationId });
    } catch (reason) {
      if (active.current) setError(errorMessage(reason));
    } finally {
      pending.current = false;
      if (active.current) setBusy(false);
    }
  }
  return <article id={anchor ? `comment-${comment.id}` : undefined}
    className={`discussion-comment ${anchor ? "is-linked" : ""}`}>
    {!editing && !comment.deleted && comment.publication ? <ReplyPublication post={comment.publication}
      commentsOpen={expanded} onComments={() => { setExpanded((value) => !value); setReplying(true); }}
      onChanged={() => { void reload(); onReaction?.(); notifyInteractionChange({ kind, id: publicationId }); }} /> : <>
    <div className="comment-byline">
      {comment.author ? <Link className="inline-flex items-center gap-2 font-semibold" to={`/@${comment.author.username}`}>
        <Avatar src={comment.author.avatars.original} name={comment.author.display_name} size="sm" />
        {comment.author.display_name}
      </Link> : <span className="text-neutral-500">{comment.deleted ? "Deleted comment" : "Unavailable account"}</span>}
      <RelativeTime publishedAt={comment.created_at} updatedAt={comment.updated_at} />
    </div>
    {editing && !comment.deleted && comment.publication ? <PublicationComposer post={comment.publication}
      label="Save changes" onCancel={() => setEditing(false)}
      onSaved={() => { setEditing(false); void reload(); notifyInteractionChange({ kind, id: publicationId }); }} /> : <p className="comment-copy">
      {comment.deleted ? "This comment was deleted. Its place in the conversation is preserved." : comment.text}
    </p>}
    </>}
    <div className="comment-actions">
      {thread && <button className="underline" aria-expanded={expanded} onClick={() => setExpanded((value) => !value)}>
        {expanded ? "Hide replies" : `View replies (${thread.replies_count})`}
      </button>}
      {thread && user && !comment.deleted && <button className="underline" aria-expanded={replying} onClick={() => setReplying((value) => !value)}>Reply</button>}
      {own && <>
        <button className="underline" disabled={busy} onClick={() => setEditing(true)}>Edit</button>
        <button className="underline" disabled={busy} onClick={() => void remove()}>Delete</button>
      </>}
    </div>
    {error && <p className="notice-error mt-2" role="alert">{error}{" "}
      <button className="underline" disabled={busy} onClick={() => void reload()}>Reload comment</button>
    </p>}
    {replying && !comment.deleted && user && <CommentForm path={base} parentId={comment.id} label="Reply to this comment"
      onCancel={() => setReplying(false)} onCreated={(created) => {
        setReplying(false);
        setExpanded(true);
        setRecentReplies((items) => [...items, created]);
        if (thread) onUpdate({ ...thread, replies_count: thread.replies_count + 1 });
        notifyInteractionChange({ kind, id: publicationId });
      }} />}
    {expanded && thread && <div className={thread.depth < 4 ? "mt-4 border-l border-neutral-200 pl-3 sm:pl-5" : "mt-4 border-t border-neutral-200"}>
      <CommentList kind={kind} id={publicationId} parentId={comment.id} newComments={recentReplies}
        onRecentUpdate={(updated) => setRecentReplies((items) => items.map((item) => item.id === updated.id ? updated : item))} />
    </div>}
  </article>;
}
