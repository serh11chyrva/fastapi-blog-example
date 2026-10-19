import type { RepostFeedItem } from "../../shared/api/types";
import { useCursorList } from "../../shared/hooks/useCursorList";
import { FeedCard } from "../feed/FeedCard";

export function ProfileReposts({ username }: { username: string }) {
  const list = useCursorList<RepostFeedItem>(`/profiles/${encodeURIComponent(username)}/reposts`);
  return <div className="space-y-4">
    {list.items.map((item) => <FeedCard key={item.id} item={item} onChanged={list.refresh} />)}
    {list.loading && <p role="status">Loading reposts…</p>}
    {list.error && <p className="notice-error" role="alert">{list.error}{" "}
      <button className="underline" onClick={list.cursor ? () => void list.loadMore() : list.refresh}>Retry</button>
    </p>}
    {!list.loading && !list.error && !list.items.length && <p className="surface p-6 text-sm text-neutral-500">
      {list.cursor ? "No available posts on this page. Continue to see older reposts." : "No reposts yet."}
    </p>}
    {list.cursor && <button className="button-secondary w-full" disabled={list.loading} onClick={() => void list.loadMore()}>Load more reposts</button>}
  </div>;
}
