import type { ProfileActivity } from "../../shared/api/types";
import { useCursorList } from "../../shared/hooks/useCursorList";
import { FeedCard } from "../feed/FeedCard";

function activityKey(item: ProfileActivity) {
  return `${item.kind}:${item.id}`;
}

export function ProfileTimeline({ username, onChanged }: { username: string; onChanged: () => void }) {
  const list = useCursorList<ProfileActivity>(`/users/${encodeURIComponent(username)}/timeline`, activityKey);
  return <div className="feed-list">
    {list.items.map((item) => <FeedCard key={activityKey(item)} item={item}
      onChanged={() => { list.refresh(); onChanged(); }} />)}
    {list.loading && <p className="list-status" role="status">Loading activity…</p>}
    {list.error && <p className="notice-error" role="alert">{list.error}{" "}
      <button className="text-link" onClick={list.cursor ? () => void list.loadMore() : list.refresh}>Retry</button>
    </p>}
    {!list.loading && !list.error && !list.items.length && !list.cursor && <p className="list-status">No public activity yet.</p>}
    {list.cursor && <button className="list-more" disabled={list.loading} onClick={() => void list.loadMore()}>Load more</button>}
  </div>;
}
