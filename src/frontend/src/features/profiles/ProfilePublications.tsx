import { useOffsetList } from "../../shared/hooks/useOffsetList";
import type { ArticleFeedItem } from "../../shared/api/types";
import { PreviewCard } from "../publications/PreviewCard";
import { useApp } from "../../app/AuthProvider";
import { InfiniteScroll } from "../../shared/ui/InfiniteScroll";
import { PublicationListSkeleton } from "../publications/PublicationSkeleton";

export function ProfilePublications({ username, pins, onChanged }: {
  username: string; pins: ArticleFeedItem[]; onChanged: () => void;
}) {
  const path = `/users/${encodeURIComponent(username)}/publications?kind=article`;
  const { user } = useApp();
  const list = useOffsetList<ArticleFeedItem>(path, 20, user?.id ?? "anonymous");
  const pinned = new Set(pins.map((item) => item.id));
  const items = list.items.filter((item) => !pinned.has(item.id));
  function changed() { list.refresh(); onChanged(); }
  return <div className="articles-panel">
    <div className="profile-article-results" aria-busy={list.loading}>
      {pins.map((item) => <PreviewCard key={`pin:${item.id}`} item={item} standalone onChanged={changed} />)}
      {items.map((item) => <PreviewCard key={item.id} item={item} standalone onChanged={changed} />)}
    </div>
    {list.loading && !list.error && <PublicationListSkeleton variant="article"
      count={list.items.length || list.hasMore || pins.length ? 2 : 3} label="Loading articles…" />}
    {list.error && <p className="notice-error" role="alert">{list.error}{" "}
      <button className="text-link" onClick={list.hasMore ? () => void list.loadMore() : list.refresh}>Retry</button>
    </p>}
    {!list.loading && !list.error && !items.length && !pins.length && <p className="list-status">No articles yet.</p>}
    <InfiniteScroll hasMore={list.hasMore} loading={list.loading} error={list.error} loadMore={list.loadMore} />
  </div>;
}
