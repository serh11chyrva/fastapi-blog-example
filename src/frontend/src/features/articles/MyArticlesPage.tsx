import { usePageTitle } from "../../app/usePageTitle";
import { useApp } from "../../app/AuthProvider";
import { useState } from "react";
import { useOffsetList } from "../../shared/hooks/useOffsetList";
import type { Article } from "../../shared/api/types";
import { Link, Navigate } from "react-router-dom";
import { EmptyState } from "../../shared/ui/EmptyState";
export function MyArticlesPage() {
  usePageTitle("My articles");
  const { user } = useApp();
  const [filter, setFilter] = useState("all");
  const { items: articles, loading, error, hasMore, loadMore } = useOffsetList<Article>(user ? `/me/articles?status=${filter}` : null);
  if (!user)
    return <Navigate to="/login" replace />;
  return <div className="utility-page space-y-5">
    <div className="flex flex-wrap items-end justify-between gap-3">
      <div>
        <p className="eyebrow">Your writing</p>
        <h1 className="page-title">My articles</h1>
      </div>
      <div className="flex gap-2">
        <select className="field w-auto py-2" value={filter} onChange={(event) => setFilter(event.target.value)} aria-label="Filter articles">
          <option value="all">All articles</option>
          <option value="draft">Drafts</option>
          <option value="scheduled">Scheduled</option>
          <option value="published">Published</option>
        </select>
        <Link className="button-primary" to="/write">Write article</Link>
      </div>
    </div>
    {error && <div className="notice-error">
      {error}
    </div>}
    {loading && !articles.length ? <p role="status">Loading articles…</p> : articles.length ? <div className="space-y-3">
      {articles.map((article) => <article className="surface p-5" key={article.id}>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <span className="badge">
              {article.status}
            </span>
            {article.thumbnail_url && <img className="mt-3 max-h-36 rounded-lg object-cover" src={article.thumbnail_url} alt="Article thumbnail" />}
            <Link to={article.status === "published" ? article.share_url || `/articles/${article.id}` : `/articles/${article.id}`} className="mt-2 block text-lg font-semibold text-slate-900 hover:text-slate-600">
              {article.title}
            </Link>
            {article.summary && <p className="mt-1 text-sm leading-6 text-slate-500">
              {article.summary}
            </p>}
            {article.scheduled_at && <p className="mt-2 text-xs text-slate-500">Scheduled for {new Date(article.scheduled_at).toLocaleString()}</p>}
            <p className="mt-2 text-xs text-slate-400">Updated {new Date(article.updated_at).toLocaleDateString()}</p>
          </div>
          <Link className="button-secondary" to={`/articles/${article.id}/edit`}>Edit</Link>
        </div>
      </article>)}
    </div> : !error && <EmptyState title="No articles yet" body="Your drafts and published articles will appear here." />}
    {hasMore && <button className="button-secondary w-full" disabled={loading} onClick={() => void loadMore()}>Load more articles</button>}
  </div>;
}
