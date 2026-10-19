import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import { Link } from "react-router-dom";
import { useApp } from "../../app/AuthProvider";
import { api, errorMessage } from "../../shared/api/client";
import type { DiscussionComment, PublicationKind } from "../../shared/api/types";
import { useCursorList } from "../../shared/hooks/useCursorList";
import { Avatar } from "../../shared/ui/Avatar";
import { notifyInteractionChange, publicationPath } from "../interactions/events";

export function Discussion({ kind, id }: { kind: PublicationKind; id: string }) {
  const { user } = useApp();
  return <section className="mt-7 border-t border-neutral-200 pt-6" aria-label={kind === "micro_post" ? "Post replies" : "Article comments"}>
    <h2 className="editorial-title text-2xl font-semibold">{kind === "micro_post" ? "Conversation" : "Comments"}</h2>
    <p className="mt-1 mb-5 text-sm text-neutral-500">
      {kind === "micro_post" ? "Reply to this note or continue a thread." : "Share a thought about this article."}
    </p>
    {!user && <p className="mb-4 text-sm"><Link className="underline" to="/login">Log in</Link> to leave a {kind === "micro_post" ? "reply" : "comment"}.</p>}
    <CommentList key={`${kind}:${id}:${user?.id ?? "anonymous"}`} kind={kind} id={id} />
  </section>;
}

function CommentForm({ path, parentId, label, onCreated, onCancel }: {
  path: string;
  parentId?: string;
  label: string;
  onCreated: (comment: DiscussionComment) => void;
  onCancel?: () => void;
}) {
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const pending = useRef(false);
  const active = useRef(true);
  useEffect(() => {
    active.current = true;
    return () => { active.current = false; };
  }, []);
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (pending.current || !text.trim()) return;
    pending.current = true;
    setBusy(true);
    setError("");
    try {
      const created = await api<DiscussionComment>(path, { method: "POST", body: JSON.stringify({ text, ...(parentId ? { parent_id: parentId } : {}) }) });
      if (!active.current) return;
      setText("");
      onCreated(created);
    } catch (reason) {
      if (active.current) setError(`${errorMessage(reason)} Your text has been kept. Reload the conversation before retrying if the result is uncertain.`);
    } finally {
      pending.current = false;
      if (active.current) setBusy(false);
    }
  }
  return <form className="my-4 space-y-2" onSubmit={submit}>
    <label className="form-label block">{label}
      <textarea className="field mt-2 min-h-24 resize-y" maxLength={5000} required value={text}
        disabled={busy} onChange={(event) => setText(event.target.value)} />
    </label>
    <div className="flex flex-wrap items-center justify-between gap-2">
      <span className="text-xs text-neutral-500">{text.length} / 5,000 · Plain text</span>
      <div className="flex gap-2">
        {onCancel && <button type="button" className="button-quiet" disabled={busy} onClick={onCancel}>Cancel</button>}
        <button className="button-secondary" disabled={busy || !text.trim()}>{busy ? "Sending…" : "Send"}</button>
      </div>
    </div>
    {error && <p role="alert" className="notice-error">{error}</p>}
  </form>;
}

function CommentList({ kind, id, parentId, newComments, onRecentUpdate }: {
  kind: PublicationKind; id: string; parentId?: string; newComments?: DiscussionComment[];
  onRecentUpdate?: (comment: DiscussionComment) => void;
}) {
  const { user } = useApp();
  const base = `${publicationPath(kind, id)}/${kind === "micro_post" ? "replies" : "comments"}`;
  const list = useCursorList<DiscussionComment>(`${base}${parentId ? `?parent_id=${encodeURIComponent(parentId)}` : ""}`);
  const [recent, setRecent] = useState<DiscussionComment[]>([]);
  useEffect(() => {
    if (newComments?.length) {
      setRecent((items) => [...items, ...newComments.filter((comment) => !items.some((item) => item.id === comment.id))]);
    }
  }, [newComments]);
  const visibleRecent = recent.filter((comment) => !list.items.some((item) => item.id === comment.id));
  function update(updated: DiscussionComment) {
    list.setItems((items) => items.map((item) => item.id === updated.id ? updated : item));
    setRecent((items) => items.map((item) => item.id === updated.id ? updated : item));
    onRecentUpdate?.(updated);
  }
  function created(comment: DiscussionComment) {
    setRecent((items) => [...items, comment]);
    notifyInteractionChange({ kind, id });
  }
  return <div>
    {user && !parentId && <CommentForm path={base} label={kind === "micro_post" ? "Your reply" : "Your comment"} onCreated={created} />}
    {visibleRecent.length > 0 && <div className="my-4 space-y-4">
      <p className="text-sm text-neutral-500" role="status">Just sent{list.cursor && " · Load more to continue the earlier conversation."}</p>
      {visibleRecent.map((comment) => <CommentItem key={comment.id} comment={comment} kind={kind} publicationId={id}
        base={base} onUpdate={update} />)}
    </div>}
    <div className="space-y-4">
      {list.items.map((comment) => <CommentItem key={comment.id} comment={comment} kind={kind} publicationId={id}
        base={base} onUpdate={update} />)}
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

function CommentItem({ comment, kind, publicationId, base, onUpdate }: {
  comment: DiscussionComment;
  kind: PublicationKind;
  publicationId: string;
  base: string;
  onUpdate: (comment: DiscussionComment) => void;
}) {
  const { user } = useApp();
  const [editing, setEditing] = useState(false);
  const [replying, setReplying] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const [recentReplies, setRecentReplies] = useState<DiscussionComment[]>([]);
  const [text, setText] = useState(comment.text ?? "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const pending = useRef(false);
  const active = useRef(true);
  useEffect(() => {
    active.current = true;
    return () => { active.current = false; };
  }, []);
  const thread = "post_id" in comment ? comment : null;
  const own = !!user && user.id === comment.author?.id && !comment.deleted;
  async function change(remove = false) {
    if (pending.current || (!remove && !text.trim())) return;
    if (remove && !window.confirm("Delete your comment? Replies will remain available.")) return;
    pending.current = true;
    setBusy(true);
    setError("");
    try {
      if (remove) {
        await api(`${base}/${comment.id}`, { method: "DELETE" });
        if (!active.current) return;
        onUpdate({ ...comment, deleted: true, text: null, author: null, updated_at: new Date().toISOString() });
      } else {
        const updated = await api<DiscussionComment>(`${base}/${comment.id}`, { method: "PATCH", body: JSON.stringify({ text }) });
        if (!active.current) return;
        onUpdate(updated);
      }
      setEditing(false);
      notifyInteractionChange({ kind, id: publicationId });
    } catch (reason) {
      if (active.current) setError(errorMessage(reason));
    } finally {
      pending.current = false;
      if (active.current) setBusy(false);
    }
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
  return <article className="min-w-0 border-t border-neutral-100 pt-4">
    <div className="flex flex-wrap items-center gap-2 text-sm">
      {comment.author ? <Link className="inline-flex items-center gap-2 font-semibold" to={`/@${comment.author.username}`}>
        <Avatar src={comment.author.avatars.original} name={comment.author.display_name} size="sm" />
        {comment.author.display_name}
      </Link> : <span className="text-neutral-500">{comment.deleted ? "Deleted comment" : "Unavailable account"}</span>}
      <time className="text-xs text-neutral-400" dateTime={comment.created_at}>{new Date(comment.created_at).toLocaleString()}</time>
    </div>
    {editing && !comment.deleted ? <form className="mt-3 space-y-2" onSubmit={(event) => { event.preventDefault(); void change(); }}>
      <label className="form-label block">Edit your comment<textarea className="field mt-2" maxLength={5000} required
        value={text} disabled={busy} onChange={(event) => setText(event.target.value)} /></label>
      <button className="button-secondary" disabled={busy || !text.trim()}>Save changes</button>{" "}
      <button type="button" className="button-quiet" disabled={busy} onClick={() => setEditing(false)}>Cancel</button>
    </form> : <p className="mt-2 whitespace-pre-wrap break-words text-sm leading-7 text-neutral-700">
      {comment.deleted ? "This comment was deleted. Its place in the conversation is preserved." : comment.text}
    </p>}
    <div className="mt-2 flex flex-wrap gap-3 text-xs text-neutral-500">
      {thread && <button className="underline" aria-expanded={expanded} onClick={() => setExpanded((value) => !value)}>
        {expanded ? "Hide replies" : `View replies (${thread.replies_count})`}
      </button>}
      {thread && user && !comment.deleted && <button className="underline" aria-expanded={replying} onClick={() => setReplying((value) => !value)}>Reply</button>}
      {own && <>
        <button className="underline" disabled={busy} onClick={() => { setText(comment.text ?? ""); setEditing(true); }}>Edit</button>
        <button className="underline" disabled={busy} onClick={() => void change(true)}>Delete</button>
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
      <CommentList kind="micro_post" id={publicationId} parentId={comment.id} newComments={recentReplies}
        onRecentUpdate={(updated) => setRecentReplies((items) => items.map((item) => item.id === updated.id ? updated : item))} />
    </div>}
  </article>;
}
