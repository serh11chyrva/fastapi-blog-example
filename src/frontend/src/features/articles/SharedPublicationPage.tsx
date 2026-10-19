import { useParams } from "react-router-dom";
import { useEffect, useState } from "react";
import type { Article, MicroPost } from "../../shared/api/types";
import { api } from "../../shared/api/client";
import { EmptyState } from "../../shared/ui/EmptyState";
import { ArticlePresentation } from "./ArticlePresentation";
import { useApp } from "../../app/AuthProvider";
import { FeedCard } from "../feed/FeedCard";
export function SharedPublicationPage() {
  const { handle = "", shareSlug = "" } = useParams();
  const username = handle.replace(/^@/, "");
  const [publication, setPublication] = useState<Article | MicroPost | null>(null);
  const [error, setError] = useState("");
  const { user } = useApp();
  const [version, setVersion] = useState(0);
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
  }, [username, shareSlug, version]);
  if (error)
    return <EmptyState title="Publication unavailable" body={error} />;
  if (!publication)
    return <div className="surface p-8 text-center text-sm text-slate-500">Loading publication…</div>;
  if (publication.kind === "article")
    return <ArticlePresentation key={publication.id} article={publication} owner={user?.id === publication.owner_id} />;
  return <div className="mx-auto max-w-2xl">
    <FeedCard key={publication.id} item={{ ...publication, published_at: publication.created_at }}
      showDiscussion onChanged={() => setVersion((value) => value + 1)} />
  </div>;
}
