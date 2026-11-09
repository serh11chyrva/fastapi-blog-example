import { usePageTitle } from "../../app/usePageTitle";
import { useApp } from "../../app/AuthProvider";
import { useState } from "react";
import { useFeed } from "./useFeed";
import { PostComposer } from "./PostComposer";
import { Link } from "react-router-dom";
import { FeedCard } from "./FeedCard";
import { EmptyState } from "../../shared/ui/EmptyState";
export function FeedPage({ following = false }: {
  following?: boolean;
}) {
  usePageTitle(following ? "Following" : "Explore");
  const { user } = useApp();
  const [kind, setKind] = useState("all");
  const [refreshKey, setRefreshKey] = useState(0);
  const feedPath = following ? "/feeds/following" : "/feeds/public";
  const { feed, busy, error, loadMore, loadingMore } = useFeed(feedPath, kind, refreshKey);
  return <div className="space-y-5">
    <div className="flex flex-wrap items-end justify-between gap-3">
      <div>
        <p className="eyebrow">Your reading room</p>
        <h1 className="page-title">
          {following ? "Following" : "Explore"}
        </h1>
        <p className="mt-1 text-sm text-slate-500">Fresh notes and stories, in the order they were shared.</p>
      </div>
      <select className="field w-auto py-2" value={kind} onChange={(event) => setKind(event.target.value)} aria-label="Filter publications">
        <option value="all">Everything</option>
        <option value="micro_post">Short notes</option>
        <option value="article">Articles</option>
      </select>
    </div>

    {!following && user && <PostComposer onPosted={() => setRefreshKey((value) => value + 1)} />}

    {error && <div className="notice-error">
      {error}
      <button className="ml-2 underline" onClick={() => setRefreshKey((value) => value + 1)}>Reload feed</button>
      {following && !user && <Link className="ml-2 font-semibold underline" to="/login">Log in</Link>}
    </div>}

    {busy ? <div className="surface p-8 text-center text-sm text-slate-500">Loading the latest posts…</div> : feed.items.length ? <div className="space-y-4">
      {feed.items.map((item) => <FeedCard key={`${item.kind}-${item.id}`} item={item} onChanged={() => setRefreshKey((value) => value + 1)} />)}
    </div> : !error && <EmptyState title={feed.next_cursor ? "No available publications on this page" : following ? "Your following feed is quiet" : "Nothing has been published yet"} body={feed.next_cursor ? "Continue to see older publications." : following ? "Follow a few profiles and their latest notes will appear here." : "Be the first to share a thought or publish an article."} />}
    {!busy && feed.next_cursor && <button className="button-secondary w-full" disabled={loadingMore} onClick={() => void loadMore()}>
      {loadingMore ? "Loading…" : "Load more"}
    </button>}

  </div>;
}
