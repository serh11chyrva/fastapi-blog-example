import { useEffect, useId, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { useApp } from "../../app/AuthProvider";
import { api, errorMessage } from "../../shared/api/client";
import type { DiscussionComment, PublicationKind } from "../../shared/api/types";
import { HashtagText } from "../../shared/text/HashtagText";
import { useCursorList } from "../../shared/hooks/useCursorList";
import { itemId, mergeListItems } from "../../shared/hooks/listItems";
import { Avatar } from "../../shared/ui/Avatar";
import { Icon } from "../../shared/ui/Icon";
import { PublicationComposer } from "../publications/PublicationComposer";
import { PublicationMenu } from "../publications/PublicationMenu";
import { ReplyPublication } from "./ReplyPublication";
import { RelativeTime } from "../../shared/ui/RelativeTime";
import { notifyInteractionChange, publicationPath } from "../interactions/events";
import { ReplySkeleton } from "./ReplySkeleton";
import { Collapsible } from "../../shared/ui/Collapsible";

function CommentForm({ path, parentId, label, onCreated, onCancel, autoFocus = false }: {
  path: string; parentId?: string; label: string; autoFocus?: boolean;
  onCreated: (comment: DiscussionComment) => void; onCancel?: () => void;
}) {
  return <PublicationComposer replyPath={path} parentId={parentId} ariaLabel={label} autoFocus={autoFocus}
    onCancel={onCancel} onSaved={(saved) => onCreated(saved as DiscussionComment)} />;
}

export function ReplyList({
  kind, id, parentId, newComments, onRecentUpdate, commentId, focusComposer = false, readOnly = false, visible = true,
}: {
  kind: PublicationKind; id: string; parentId?: string; newComments?: DiscussionComment[];
  onRecentUpdate?: (comment: DiscussionComment) => void;
  commentId?: string;
  focusComposer?: boolean;
  readOnly?: boolean;
  visible?: boolean;
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
    if (visible && commentId && linkReady)
      document.getElementById(`comment-${commentId}`)?.scrollIntoView({ block: "center" });
  }, [commentId, linkReady, visible]);
  useEffect(() => {
    if (newComments?.length) {
      setRecent((items) => mergeListItems(items, newComments, itemId));
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
    setRecent((items) => mergeListItems(items, [comment], itemId));
    notifyInteractionChange({ kind, id });
  }
  function renderComment(comment: DiscussionComment) {
    return <ReplyThread key={comment.id} comment={comment} kind={kind} publicationId={id}
      base={base} onUpdate={update}
      readOnly={readOnly} anchor={comment.id === commentId} onReaction={kind === "article" && sort === "most_liked" ? list.refresh : undefined} />;
  }
  return <div>
    {!parentId && <div className="discussion-header">
      <h2>Replies</h2>
      {kind === "article" && <select className="discussion-sort" aria-label="Sort comments" value={sort} onChange={(event) =>
        setSort(event.target.value === "newest" ? "newest" : "most_liked")}>
        <option value="most_liked">Most liked</option><option value="newest">Newest first</option>
      </select>}
    </div>}
    {user && !readOnly && !parentId && <CommentForm path={base} label="Your reply" autoFocus={focusComposer} onCreated={created} />}
    {commentId && linked?.id === commentId && !listed && <div className="my-4">
      <p className="text-xs font-semibold text-neutral-600">Linked comment</p>
      {renderComment(linked)}
    </div>}
    {linkError && <p className="notice-error" role="alert">{linkError}</p>}
    {visibleRecent.length > 0 && <div className="my-4 space-y-4">
      <p className="text-sm text-neutral-500" role="status">Just sent{list.cursor && " · Load more to continue the earlier conversation."}</p>
      {visibleRecent.map(renderComment)}
    </div>}
    <div className="space-y-4" aria-busy={list.loading}>
      {list.items.map(renderComment)}
    </div>
    {list.loading && !list.error && <ReplySkeleton />}
    {list.error && <p role="alert" className="notice-error mt-3">{list.error}{" "}
      <button className="underline" onClick={list.cursor ? () => void list.loadMore() : list.refresh}>Retry</button>
    </p>}
    {!list.loading && !list.error && !list.items.length && !visibleRecent.length && <p className="py-3 text-sm text-neutral-500">
      {readOnly || parentId ? "No replies yet." : "No replies yet. Be the first to reply."}
    </p>}
    {list.cursor && <button className="button-secondary mt-4" disabled={list.loading} onClick={() => void list.loadMore()}>Load more</button>}
  </div>;
}

export function ReplyThread({ comment, kind, publicationId, base, onUpdate, onReaction, anchor, readOnly: inheritedReadOnly = false }: {
  comment: DiscussionComment;
  kind: PublicationKind;
  publicationId: string;
  base: string;
  onUpdate: (comment: DiscussionComment) => void;
  onReaction?: () => void;
  anchor?: boolean;
  readOnly?: boolean;
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
  const menu = useRef<HTMLDetailsElement>(null);
  useEffect(() => {
    active.current = true;
    return () => { active.current = false; };
  }, []);
  const thread = comment;
  const readOnly = inheritedReadOnly || !!comment.publication?.archived_at || !!comment.publication?.read_only;
  const own = !!user && user.id === comment.author?.id && !comment.deleted;
  const replyFormId = useId();

  function toggleReply() {
    if (!user || readOnly) { setExpanded((value) => !value); return; }
    if (comment.deleted) return;
    setReplying((value) => !value);
  }

  function beginEdit() {
    menu.current?.removeAttribute("open");
    setReplying(false);
    setEditing(true);
  }
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
    className={`discussion-comment motion-enter ${anchor ? "is-linked" : ""}`}>
    {!editing && !comment.deleted && comment.publication ? <ReplyPublication post={comment.publication}
      readOnly={readOnly} commentsOpen={user && !readOnly ? replying : expanded} onComments={toggleReply}
      onChanged={(action) => { void reload(); if (action === "like") onReaction?.(); }}
      menu={own && <PublicationMenu item={comment.publication} menuRef={menu} disabled={busy} readOnly={readOnly}
        onReconciled={(updated) => {
          if (updated.kind === "micro_post") onUpdate({
            ...comment, publication: updated, text: updated.text, updated_at: updated.updated_at,
          });
        }} onChanged={() => void reload()}>
        <button type="button" disabled={busy} onClick={beginEdit}>Edit</button>
        <button type="button" disabled={busy} onClick={() => {
          menu.current?.removeAttribute("open"); void remove();
        }}>Delete</button>
      </PublicationMenu>} /> : <>
    <div className="comment-byline">
      {comment.author ? <span className="inline-flex items-center gap-2 font-semibold">
        <Link to={`/@${comment.author.username}`}><Avatar src={comment.author.avatars.original} name={comment.author.display_name} size="sm" /></Link>
        <HashtagText text={comment.author.display_name} href={`/@${comment.author.username}`} />
      </span> : <span className="text-neutral-500">{comment.deleted ? "Deleted comment" : "Unavailable account"}</span>}
      <RelativeTime publishedAt={comment.created_at} updatedAt={comment.updated_at} />
    </div>
    {editing && !comment.deleted && comment.publication ? <PublicationComposer post={comment.publication}
      label="Save changes" onCancel={() => setEditing(false)}
      onSaved={() => { setEditing(false); void reload(); notifyInteractionChange({ kind, id: publicationId }); }} /> : <p className="comment-copy">
      {comment.deleted ? "This comment was deleted. Its place in the conversation is preserved." : <HashtagText text={comment.text ?? ""} />}
    </p>}
    </>}
    {(thread.replies_count > 0 || (!comment.publication && user && !readOnly && !comment.deleted)) && <div className="comment-actions">
      {thread.replies_count > 0 && <button type="button" className="text-link" aria-expanded={expanded}
        onClick={() => setExpanded((value) => !value)}>
        {expanded ? "Hide replies" : `Show replies (${thread.replies_count})`}
      </button>}
      {!comment.publication && user && !readOnly && !comment.deleted && <button type="button" className="text-link"
        aria-expanded={replying} aria-controls={replyFormId} onClick={toggleReply}><Icon name="comment" />Reply</button>}
    </div>}
    {error && <p className="notice-error mt-2" role="alert">{error}{" "}
      <button className="underline" disabled={busy} onClick={() => void reload()}>Reload comment</button>
    </p>}
    {!readOnly && !comment.deleted && user && <Collapsible id={replyFormId} className="inline-reply-composer" open={replying}>
      <CommentForm path={base} parentId={comment.id} label="Reply to this reply" autoFocus={replying}
      onCancel={() => setReplying(false)} onCreated={(created) => {
        setReplying(false);
        setExpanded(true);
        setRecentReplies((items) => mergeListItems(items, [created], itemId));
        if (thread && !recentReplies.some((item) => item.id === created.id))
          onUpdate({ ...thread, replies_count: thread.replies_count + 1 });
        notifyInteractionChange({ kind, id: publicationId });
      }} />
    </Collapsible>}
    <Collapsible open={expanded} className={thread.depth < 4 ? "mt-4 border-l border-neutral-200 pl-3 sm:pl-5" : "mt-4 border-t border-neutral-200"}>
      <ReplyList kind={kind} id={publicationId} parentId={comment.id} readOnly={readOnly} newComments={recentReplies}
        onRecentUpdate={(updated) => setRecentReplies((items) => items.map((item) => item.id === updated.id ? updated : item))} />
    </Collapsible>
  </article>;
}
