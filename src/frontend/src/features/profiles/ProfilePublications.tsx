import { useOffsetList } from "../../shared/hooks/useOffsetList";
import type { ArticleFeedItem } from "../../shared/api/types";
import { PreviewCard } from "../publications/PreviewCard";

export function ProfilePublications({ username }: { username: string }) {
  const path = `/users/${encodeURIComponent(username)}/publications?kind=article`;
  const list = useOffsetList<ArticleFeedItem>(path, 20);
  return <div className="articles-panel">
    {list.items.map((item) => <PreviewCard key={item.id} item={item} standalone />)}
    {list.loading && <p className="list-status" role="status">Loading articles…</p>}
    {list.error && <p className="notice-error" role="alert">{list.error}</p>}
    {!list.loading && !list.error && !list.items.length && <p className="list-status">No articles yet.</p>}
    {list.hasMore && <button className="list-more" disabled={list.loading} onClick={() => void list.loadMore()}>Load more</button>}
  </div>;
}
