import { useParams } from "react-router-dom";
import { useApp } from "../../app/AuthProvider";
import { useEffect, useState } from "react";
import type { Article } from "../../shared/api/types";
import { api } from "../../shared/api/client";
import { EmptyState } from "../../shared/ui/EmptyState";
import { ArticlePresentation } from "./ArticlePresentation";
export function ArticlePage() {
  const { articleId = "" } = useParams();
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
  }, [articleId]);
  if (error)
    return <EmptyState title="Article unavailable" body={error} />;
  if (!article)
    return <div className="surface p-8 text-center text-sm text-slate-500">Loading article…</div>;
  return <ArticlePresentation article={article} owner={user?.id === article.author_id} />;
}
