import { useOffsetList } from "../../shared/hooks/useOffsetList";
import type { ArticleFeedItem } from "../../shared/api/types";
import { PreviewCard } from "../publications/PreviewCard";
import { useApp } from "../../app/AuthProvider";
import { InfiniteScroll } from "../../shared/ui/InfiniteScroll";

export function ProfilePublications({ username }: { username: string }) {
  const path = `/users/${encodeURIComponent(username)}/publications?kind=article`;
  const { user } = useApp();
  const list = useOffsetList<ArticleFeedItem>(path, 20, user?.id ?? "anonymous");
  return <div className="articles-panel">
    {list.items.map((item) => <PreviewCard key={item.id} item={item} standalone />)}
    {list.loading && <p className="list-status" role="status">Loading articles…</p>}
    {list.error && <p className="notice-error" role="alert">{list.error}{" "}
      <button className="text-link" onClick={list.hasMore ? () => void list.loadMore() : list.refresh}>Retry</button>
    </p>}
    {!list.loading && !list.error && !list.items.length && <p className="list-status">No articles yet.</p>}
    <InfiniteScroll hasMore={list.hasMore} loading={list.loading} error={list.error} loadMore={list.loadMore} />
  </div>;
}
