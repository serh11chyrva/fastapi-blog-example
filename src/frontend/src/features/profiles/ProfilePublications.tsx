import { useOffsetList } from "../../shared/hooks/useOffsetList";
import type { OriginalFeedItem } from "../../shared/api/types";
import { FeedCard } from "../feed/FeedCard";

export function ProfilePublications({ username, kind, onChanged }: {
  username: string;
  kind: "micro_post" | "article";
  onChanged: () => void;
}) {
  const list = useOffsetList<OriginalFeedItem>(`/users/${encodeURIComponent(username)}/publications?kind=${kind}`, 20);
  return <div className="space-y-4">
    {list.items.map((item) => <FeedCard key={item.id} item={item} onChanged={onChanged} />)}
    {list.loading && <p role="status">Loading publications…</p>}
    {list.error && <p className="notice-error" role="alert">{list.error}{" "}<button className="underline" onClick={onChanged}>Retry</button></p>}
    {!list.loading && !list.error && !list.items.length && <p className="surface p-6 text-sm text-neutral-500">No {kind === "article" ? "articles" : "posts"} yet.</p>}
    {list.hasMore && <button className="button-secondary w-full" disabled={list.loading} onClick={() => void list.loadMore()}>Load more</button>}
  </div>;
}
