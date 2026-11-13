import { usePageTitle } from "../../app/usePageTitle";
import { useParams } from "react-router-dom";
import { useEffect, useState } from "react";
import type { Article, MicroPost } from "../../shared/api/types";
import { api } from "../../shared/api/client";
import { EmptyState } from "../../shared/ui/EmptyState";
import { ArticlePresentation } from "./ArticlePresentation";
import { useApp } from "../../app/AuthProvider";
import { PostDetail } from "../feed/PostDetail";
import { PublicationPageSkeleton } from "../publications/PublicationSkeleton";
export function SharedPublicationPage() {
  const { user } = useApp();
  const { handle = "", shareSlug = "" } = useParams();
  return <SharedPublicationContent key={`${handle}/${shareSlug}:${user?.id ?? "anonymous"}`} handle={handle} shareSlug={shareSlug} />;
}

function SharedPublicationContent({ handle, shareSlug }: { handle: string; shareSlug: string }) {
  const username = handle.replace(/^@/, "");
  const [publication, setPublication] = useState<Article | MicroPost | null>(null);
  const [error, setError] = useState("");
  const { user } = useApp();
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
  }, [username, shareSlug, user?.id]);
  usePageTitle(error ? "Publication unavailable" : publication?.kind === "article" ? publication.title
    : publication ? `Post by ${publication.authors[0]?.display_name ?? "Unknown author"}` : "Loading publication");
  if (publication && (publication.archived_at || (publication.kind === "article" && publication.status !== "published"))
      && user?.id !== publication.owner_id) return <PublicationPageSkeleton />;
  if (error)
    return <EmptyState title="Publication unavailable" body={error} />;
  if (!publication)
    return <PublicationPageSkeleton />;
  if (publication.kind === "article")
    return <ArticlePresentation key={publication.id} article={publication} owner={user?.id === publication.owner_id} onChanged={setPublication} />;
  return <PostDetail key={`${publication.id}:${user?.id ?? "anonymous"}`} postId={publication.id} />;
}
