import { useApp } from "../../app/AuthProvider";
import type { OriginalFeedItem } from "../../shared/api/types";
import { useCursorList } from "../../shared/hooks/useCursorList";
import { InfiniteScroll } from "../../shared/ui/InfiniteScroll";
import { FeedCard } from "../feed/FeedCard";
import { PublicationListSkeleton } from "../publications/PublicationSkeleton";

function archiveKey(item: OriginalFeedItem) { return `${item.kind}:${item.id}`; }

export function ProfileArchive() {
  const { user } = useApp();
  return user ? <ArchiveContent key={user.id} ownerId={user.id} /> : null;
}

function ArchiveContent({ ownerId }: { ownerId: string }) {
  const list = useCursorList<OriginalFeedItem>("/me/archive", archiveKey, ownerId);
  return <div className="feed-list" aria-label="Your private archive">
    <p className="list-status">Only you can see these publications. Unarchive a publication to restore its usual visibility.</p>
    <div aria-busy={list.loading}>
      {list.items.map((item) => <FeedCard key={archiveKey(item)} item={item} onChanged={list.refresh} />)}
    </div>
    {list.loading && !list.error && <PublicationListSkeleton count={list.items.length || list.cursor ? 2 : 3}
      label="Loading archive…" />}
    {list.error && <p className="notice-error" role="alert">{list.error}{" "}
      <button type="button" className="text-link" onClick={list.cursor ? () => void list.loadMore() : list.refresh}>Retry</button>
    </p>}
    {!list.loading && !list.error && !list.items.length && !list.cursor && <p className="list-status">Your archive is empty.</p>}
    <InfiniteScroll hasMore={!!list.cursor} loading={list.loading} error={list.error} loadMore={list.loadMore} />
  </div>;
}
