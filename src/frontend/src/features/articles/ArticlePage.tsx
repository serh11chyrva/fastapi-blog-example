import { usePageTitle } from "../../app/usePageTitle";
import { useParams } from "react-router-dom";
import { useApp } from "../../app/AuthProvider";
import { useEffect, useState } from "react";
import type { Article } from "../../shared/api/types";
import { api } from "../../shared/api/client";
import { EmptyState } from "../../shared/ui/EmptyState";
import { ArticlePresentation } from "./ArticlePresentation";
import { PublicationPageSkeleton } from "../publications/PublicationSkeleton";
export function ArticlePage() {
  const { user } = useApp();
  const { articleId = "" } = useParams();
  return <ArticleContent key={`${articleId}:${user?.id ?? "anonymous"}`} articleId={articleId} />;
}

function ArticleContent({ articleId }: { articleId: string }) {
  const { user } = useApp();
  const [article, setArticle] = useState<Article | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    setArticle(null);
    setError("");
    api<Article>(`/articles/${articleId}`, { signal: controller.signal })
      .then((value) => {
        if (!controller.signal.aborted)
          setArticle(value);
      })
      .catch((reason: unknown) => {
        if (!controller.signal.aborted)
          setError(reason instanceof Error ? reason.message : "Could not load this page.");
      });
    return () => controller.abort();
  }, [articleId, user?.id]);
  usePageTitle(error ? "Article unavailable" : article?.title ?? "Loading article");
  if (article && (article.archived_at || article.status !== "published") && user?.id !== article.owner_id)
    return <PublicationPageSkeleton kind="article" />;
  if (error)
    return <EmptyState title="Article unavailable" body={error} />;
  if (!article)
    return <PublicationPageSkeleton kind="article" />;
  return <ArticlePresentation key={article.id} article={article} owner={user?.id === article.owner_id} onChanged={setArticle} />;
}
