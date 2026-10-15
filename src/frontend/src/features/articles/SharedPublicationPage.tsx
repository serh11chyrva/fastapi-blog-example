import { Link, useParams } from "react-router-dom";
import { useEffect, useState } from "react";
import type { Article, MicroPost } from "../../shared/api/types";
import { api } from "../../shared/api/client";
import { EmptyState } from "../../shared/ui/EmptyState";
import { ArticlePresentation } from "./ArticlePresentation";
import { Avatar } from "../../shared/ui/Avatar";
export function SharedPublicationPage() {
  const { handle = "", shareSlug = "" } = useParams();
  const username = handle.replace(/^@/, "");
  const [publication, setPublication] = useState<Article | MicroPost | null>(null);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);
  useEffect(() => {
    const controller = new AbortController();
    setPublication(null);
    setError("");
    api<Article | MicroPost>(`/publications/${encodeURIComponent(username)}/${encodeURIComponent(shareSlug)}`, { signal: controller.signal })
      .then((value) => {
        if (!controller.signal.aborted)
          setPublication(value);
      })
      .catch((reason: unknown) => {
        if (!controller.signal.aborted)
          setError(reason instanceof Error ? reason.message : "Could not load this page.");
      });
    return () => controller.abort();
  }, [username, shareSlug]);
  if (error)
    return <EmptyState title="Publication unavailable" body={error} />;
  if (!publication)
    return <div className="surface p-8 text-center text-sm text-slate-500">Loading publication…</div>;
  if (publication.kind === "article")
    return <ArticlePresentation article={publication} owner={false} />;
  return <article className="surface mx-auto max-w-2xl p-6 sm:p-9">
    <Link className="flex items-center gap-3" to={`/@${publication.author_username}`}>
      <Avatar src={publication.author_avatar_url} name={publication.author_display_name} />
      <div>
        <p className="font-semibold text-slate-900">
          {publication.author_display_name}
        </p>
        <p className="text-sm text-slate-500">@{publication.author_username}</p>
      </div>
    </Link>
    <p className="mt-8 whitespace-pre-wrap text-xl leading-9 text-slate-800">
      {publication.text}
    </p>
    {!!publication.images?.length && <div className={`post-gallery mt-4 ${publication.images.length === 1 ? "single" : ""}`}>
      {publication.images.map((src, index) => <img src={src} key={src} alt={`Post image ${index + 1}`} />)}
    </div>}
    <div className="mt-6 flex items-center justify-between border-t border-slate-100 pt-4">
      <time className="text-sm text-slate-400">
        {new Date(publication.created_at).toLocaleString()}
      </time>
      <button className="button-secondary" onClick={() => {
        const url = publication.share_url && new URL(publication.share_url, window.location.origin).toString(); if (url)
          void navigator.clipboard.writeText(url).then(() => { setCopied(true); window.setTimeout(() => setCopied(false), 1800); });
      }}>
        {copied ? "Link copied" : "Share"}
      </button>
    </div>
  </article>;
}
