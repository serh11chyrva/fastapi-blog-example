import type { PostFeedItem, ProfileActivity } from "../../shared/api/types";
import { useCursorList } from "../../shared/hooks/useCursorList";
import { FeedCard } from "../feed/FeedCard";
import { useApp } from "../../app/AuthProvider";
import { InfiniteScroll } from "../../shared/ui/InfiniteScroll";

function activityKey(item: ProfileActivity) { return `${item.kind}:${item.id}`; }

export function ProfileTimeline({ username, pins, onChanged }: {
  username: string; pins: PostFeedItem[]; onChanged: () => void;
}) {
  const { user } = useApp();
  const list = useCursorList<ProfileActivity>(`/users/${encodeURIComponent(username)}/timeline`, activityKey, user?.id ?? "anonymous");
  const pinned = new Set(pins.map((item) => item.id));
  const items = list.items.filter((item) => item.kind === "repost" || !pinned.has(item.id));
  function changed() { list.refresh(); onChanged(); }
  return <div className="feed-list">
    {pins.map((item) => <FeedCard key={`pin:${item.id}`} item={item} onChanged={changed} />)}
    {items.map((item) => <FeedCard key={activityKey(item)} item={item} onChanged={changed} />)}
    {list.loading && <p className="list-status" role="status">Loading activity…</p>}
    {list.error && <p className="notice-error" role="alert">{list.error}{" "}
      <button className="text-link" onClick={list.cursor ? () => void list.loadMore() : list.refresh}>Retry</button>
    </p>}
    {!list.loading && !list.error && !items.length && !pins.length && !list.cursor && <p className="list-status">No public activity yet.</p>}
    <InfiniteScroll hasMore={!!list.cursor} loading={list.loading} error={list.error} loadMore={list.loadMore} />
  </div>;
}
