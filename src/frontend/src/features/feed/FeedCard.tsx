import type { FeedItem } from "../../shared/api/types";
import { useApp } from "../../app/AuthProvider";
import { useState } from "react";
import { api, errorMessage } from "../../shared/api/client";
import { Link } from "react-router-dom";
import { Avatar } from "../../shared/ui/Avatar";
export function FeedCard({ item, onChanged }: {
  item: FeedItem;
  onChanged: () => void;
}) {
  const { user } = useApp();
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);
  const [editing, setEditing] = useState(false);
  const [editText, setEditText] = useState(item.text || "");
  const isOwner = user?.id === item.author_id;
  async function share() {
    if (!item.share_url)
      return;
    await navigator.clipboard.writeText(new URL(item.share_url, window.location.origin).toString());
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1800);
  }
  async function removePost() {
    if (!confirm("Remove this note from the public feed?"))
      return;
    try {
      await api(`/posts/${item.id}`, { method: "DELETE" });
      onChanged();
    }
    catch (reason) {
      setError(errorMessage(reason));
    }
  }
  async function savePostEdit() {
    try {
      await api(`/posts/${item.id}`, { method: "PATCH", body: JSON.stringify({ text: editText }) });
      setEditing(false);
      onChanged();
    }
    catch (reason) {
      setError(errorMessage(reason));
    }
  }
  return <article className="surface p-5 sm:p-6">
    <div className="flex items-start gap-3">
      <Link to={`/@${item.author_username}`}>
        <Avatar src={item.author_avatar_url} name={item.author_display_name} />
      </Link>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-x-2">
          <Link to={`/@${item.author_username}`} className="font-semibold text-slate-900 hover:text-slate-600">
            {item.author_display_name}
          </Link>
          <span className="text-sm text-slate-400">@{item.author_username}</span>
          <span className="text-slate-300">·</span>
          <time className="text-sm text-slate-400">
            {new Date(item.published_at).toLocaleDateString("en", { month: "short", day: "numeric" })}
          </time>
        </div>

        {item.kind === "micro_post" ? editing ? <div className="mt-3 space-y-2">
          <textarea className="field min-h-24 resize-y" maxLength={280} value={editText} onChange={(event) => setEditText(event.target.value)} />
          <div className="flex justify-end gap-2">
            <button className="button-quiet" onClick={() => setEditing(false)}>Cancel</button>
            <button className="button-secondary" onClick={() => void savePostEdit()}>Save note</button>
          </div>
        </div> : <>
          <p className="mt-2 whitespace-pre-wrap text-[15px] leading-7 text-slate-800">
            {item.text}
          </p>
          {!!item.images?.length && <div className={`post-gallery mt-4 ${item.images.length === 1 ? "single" : ""}`}>
            {item.images.map((src, index) => <img src={src} key={src} alt={`Post image ${index + 1}`} loading="lazy" />)}
          </div>}
        </> : <Link to={item.share_url || `/articles/${item.id}`} className="mt-3 block overflow-hidden border border-neutral-200 transition hover:border-black">
          {item.thumbnail_url && <img className="max-h-64 w-full object-cover" src={item.thumbnail_url} alt="Article thumbnail" />}
          <div className="p-4">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">Article</span>
            <h2 className="editorial-title mt-1 text-xl font-semibold leading-7 text-black">
              {item.title}
            </h2>
            {item.summary && <p className="mt-1 text-sm leading-6 text-slate-600">
              {item.summary}
            </p>}
            <span className="mt-3 inline-flex text-sm font-semibold text-slate-700">Read article <span className="ml-1">→</span></span>
          </div>
        </Link>}

        <div className="mt-4 flex items-center justify-between border-t border-slate-100 pt-3">
          <span className="text-xs text-slate-400">
            {item.kind === "micro_post" ? "Short note" : "Long-form story"}
          </span>
          <div className="flex items-center gap-2">
            <button className="text-xs font-medium text-slate-500 hover:text-slate-900" onClick={() => void share()}>
              {copied ? "Link copied" : "Share"}
            </button>
            {isOwner && item.kind === "micro_post" && <>
              <button className="text-xs font-medium text-slate-500 hover:text-slate-900" onClick={() => setEditing((value) => !value)}>Edit note</button>
              <button className="text-xs font-medium text-slate-400 hover:text-slate-700" onClick={removePost}>Delete note</button>
            </>}
          </div>
        </div>
        {error && <p className="mt-2 text-sm text-slate-700">
          {error}
        </p>}

      </div>
    </div>
  </article>;
}
