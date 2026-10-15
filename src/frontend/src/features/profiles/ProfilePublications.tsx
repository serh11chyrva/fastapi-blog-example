import { useOffsetList } from "../../shared/hooks/useOffsetList";
import type { FeedItem } from "../../shared/api/types";
import { EmptyState } from "../../shared/ui/EmptyState";
import { Link } from "react-router-dom";
import { FeedCard } from "../feed/FeedCard";
export function ProfilePublications({ username, kind, onChanged }: {
  username: string;
  kind: "micro_post" | "article";
  onChanged: () => void;
}) {
  const { items, loading, error, hasMore, loadMore } = useOffsetList<FeedItem>(`/users/${encodeURIComponent(username)}/publications?kind=${kind}`, 20);
  if (loading && !items.length)
    return <div className="surface p-6 text-sm text-slate-500">Loading publications…</div>;
  if (error && !items.length)
    return <EmptyState title="Publications unavailable" body={error} />;
  return <>
    <div className={kind === "article" ? "grid gap-4 sm:grid-cols-2" : "space-y-4"}>
      {items.length ? items.map((item) => kind === "article" ? <Link className="article-card" key={item.id} to={item.share_url || `/articles/${item.id}`}>
        <div className={`article-card-image ${item.thumbnail_url ? "has-image" : ""}`}>
          {item.thumbnail_url && <img src={item.thumbnail_url} alt="" loading="lazy" />}
        </div>
        <div className="p-4">
          <p className="eyebrow">Article</p>
          <h2 className="editorial-title mt-1 text-xl font-semibold leading-7 text-black">
            {item.title}
          </h2>
          {item.summary && <p className="mt-2 line-clamp-3 text-sm leading-6 text-neutral-600">
            {item.summary}
          </p>}
          <time className="mt-4 block text-xs text-neutral-400">
            {new Date(item.published_at).toLocaleDateString()}
          </time>
        </div>
      </Link> : <FeedCard key={item.id} item={item} onChanged={onChanged} />) : <EmptyState title={kind === "article" ? "No articles yet" : "No posts yet"} body="When this writer publishes something, it will appear here." />}
    </div>
    {error && <div className="notice-error">
      {error}
    </div>}
    {hasMore && <button className="button-secondary mt-4 w-full" disabled={loading} onClick={() => void loadMore()}>Load more</button>}
  </>;
}
