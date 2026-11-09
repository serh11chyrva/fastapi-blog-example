import { useState } from "react";
import { Link } from "react-router-dom";
import { useApp } from "../../app/AuthProvider";
import { api, errorMessage } from "../../shared/api/client";
import type { FeedItem, OriginalFeedItem } from "../../shared/api/types";
import { HighlightedReplies } from "../comments/HighlightedReplies";
import { Discussion } from "../comments/Discussion";
import { PublicationActions } from "../interactions/PublicationActions";
import { Attachments } from "../publications/Attachments";
import { PublicationAuthors } from "../publications/PublicationAuthors";

export function FeedCard({ item, onChanged, showDiscussion = false }: {
  item: FeedItem;
  onChanged: () => void;
  showDiscussion?: boolean;
}) {
  return <article className="surface p-5 sm:p-6">
    {item.kind === "repost" && <div className="mb-4 border-b border-neutral-100 pb-3 text-sm text-neutral-500">
      ↻ <Link className="font-semibold underline" to={`/@${item.reposted_by.username}`}>{item.reposted_by.display_name}</Link>
      {" "}reposted · <time dateTime={item.published_at}>{new Date(item.published_at).toLocaleString()}</time>
    </div>}
    <OriginalCard key={item.kind === "repost" ? item.post.id : item.id}
      item={item.kind === "repost" ? item.post : item} onChanged={onChanged} showDiscussion={showDiscussion} />
  </article>;
}

function OriginalCard({ item, onChanged, showDiscussion }: {
  item: OriginalFeedItem; onChanged: () => void; showDiscussion: boolean;
}) {
  const { user } = useApp();
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);
  const [editing, setEditing] = useState(false);
  const [text, setText] = useState(item.kind === "micro_post" ? item.text : "");
  const [busy, setBusy] = useState(false);
  const [comments, setComments] = useState(showDiscussion);
  const own = user?.id === item.owner_id;
  const page = item.share_url || (item.kind === "micro_post" ? `/posts/${item.id}` : `/articles/${item.id}`);
  async function share() {
    try {
      await navigator.clipboard.writeText(new URL(page, window.location.origin).toString());
      setCopied(true);
    } catch (reason) { setError(errorMessage(reason)); }
  }
  async function changePost(remove = false) {
    if (busy || (remove && !window.confirm("Delete this note?"))) return;
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
  return <>
    <PublicationAuthors authors={item.authors} />
    <time className="mt-2 block text-xs text-neutral-400" dateTime={item.published_at}>
      {new Date(item.published_at).toLocaleString()}
    </time>
    {item.kind === "micro_post" ? <>
      {editing ? <form className="mt-4 space-y-2" onSubmit={(event) => { event.preventDefault(); void changePost(); }}>
        <label className="form-label block">Edit note<textarea className="field mt-2 min-h-24" maxLength={280}
          value={text} disabled={busy} onChange={(event) => setText(event.target.value)} /></label>
        <button className="button-secondary" disabled={busy || !text.trim()}>Save note</button>{" "}
        <button type="button" className="button-quiet" disabled={busy} onClick={() => setEditing(false)}>Cancel</button>
      </form> : <p className="mt-3 whitespace-pre-wrap break-words text-[15px] leading-7">{item.text}</p>}
      <Attachments items={item.attachments} />
    </> : <Link to={page} className="mt-4 block overflow-hidden border border-neutral-200 hover:border-black">
      {item.thumbnail_url && <img className="max-h-64 w-full object-cover" src={item.thumbnail_url} alt="Article cover" />}
      <div className="p-4"><span className="eyebrow">Article</span>
        <h2 className="editorial-title mt-1 text-xl font-semibold">{item.title}</h2>
        {item.summary && <p className="mt-2 text-sm leading-6 text-neutral-600">{item.summary}</p>}
        <span className="mt-3 block text-sm font-semibold">Read article →</span>
      </div>
    </Link>}
    <PublicationActions key={`${item.kind}:${item.id}`} kind={item.kind} id={item.id}
      onComments={() => setComments((value) => !value)}
      onChanged={(action) => { if (action === "repost") onChanged(); }} />
    <div className="mt-3 flex flex-wrap gap-3 text-xs text-neutral-500">
      <Link className="underline" to={page}>Open {item.kind === "micro_post" ? "note" : "article"}</Link>
      <button className="underline" onClick={() => void share()}>{copied ? "Link copied" : "Share link"}</button>
      {own && item.kind === "micro_post" && <>
        <button className="underline" disabled={busy} onClick={() => { setText(item.text); setEditing(true); }}>Edit note</button>
        <button className="underline" disabled={busy} onClick={() => void changePost(true)}>Delete note</button>
      </>}
    </div>
    {error && <p className="notice-error mt-3" role="alert">{error}</p>}
    {item.kind === "micro_post" && !comments &&
      <HighlightedReplies postId={item.id} openDiscussion={() => setComments(true)} />}
    {comments && <Discussion key={`${item.kind}:${item.id}`} kind={item.kind} id={item.id} />}
  </>;
}
