import { useEffect, useState } from "react";
import { usePageTitle } from "../../app/usePageTitle";
import { publicationEvent } from "../interactions/events";
import { FeedCard } from "./FeedCard";
import { useFeed } from "./useFeed";

export function FeedPage({ following = false }: { following?: boolean }) {
  usePageTitle(following ? "Following" : "Explore");
  const [kind, setKind] = useState("all");
  const [refreshKey, setRefreshKey] = useState(0);
  const feedPath = following ? "/feeds/following" : "/feeds/public";
  const { feed, busy, error, loadMore, loadingMore } = useFeed(feedPath, kind, refreshKey);

  useEffect(() => {
    function refresh() { setRefreshKey((value) => value + 1); }
    window.addEventListener(publicationEvent, refresh);
    return () => window.removeEventListener(publicationEvent, refresh);
  }, []);

  return <section className="feed-list" aria-label={following ? "Following" : "Explore"}>
    <header className="feed-heading">
      <h1>{following ? "Following" : "Explore"}</h1>
      <select className="feed-filter" value={kind} onChange={(event) => setKind(event.target.value)} aria-label="Filter publications">
        <option value="all">Everything</option><option value="micro_post">Posts</option><option value="article">Articles</option>
      </select>
    </header>
    {error && <p className="notice-error" role="alert">{error}{" "}
      <button className="text-link" onClick={() => setRefreshKey((value) => value + 1)}>Reload feed</button>
    </p>}
    {busy && <p className="list-status" role="status">Loading publications…</p>}
    {!busy && !error && !feed.items.length && <p className="list-status">
      {following ? "Follow a writer to see their publications here." : "There are no publications yet."}
    </p>}
    {feed.items.map((item) => <FeedCard key={`${item.kind}:${item.id}`} item={item} onChanged={() => setRefreshKey((value) => value + 1)} />)}
    {feed.next_cursor && <button type="button" className="list-more" onClick={() => void loadMore()} disabled={loadingMore}>
      {loadingMore ? "Loading…" : "Load more"}
    </button>}
  </section>;
}
