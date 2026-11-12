import { usePageTitle } from "../../app/usePageTitle";
import { useEffect } from "react";
import { useApp } from "../../app/AuthProvider";
import type { SavedPublication } from "../../shared/api/types";
import { useCursorList } from "../../shared/hooks/useCursorList";
import { InfiniteScroll } from "../../shared/ui/InfiniteScroll";
import { FeedCard } from "../feed/FeedCard";
import { interactionEvent, publicationStateEvent } from "./events";
import type { InteractionChange } from "./events";
import { PublicationListSkeleton } from "../publications/PublicationSkeleton";

export function SavedPage() {
  usePageTitle("Saved");
  const { user } = useApp();
  return <SavedList key={user?.id} />;
}

function SavedList() {
  const list = useCursorList<SavedPublication>("/me/saved");
  const { setItems } = list;
  useEffect(() => {
    window.addEventListener(publicationStateEvent, list.refresh);
    return () => window.removeEventListener(publicationStateEvent, list.refresh);
  }, [list.refresh]);
  useEffect(() => {
    function changed(event: Event) {
      const detail = (event as CustomEvent<InteractionChange>).detail;
      if (detail.action === "save" && detail.enabled === false) {
        setItems((items) => items.filter((item) => item.publication.id !== detail.id || item.publication.kind !== detail.kind));
      }
    }
    window.addEventListener(interactionEvent, changed);
    return () => window.removeEventListener(interactionEvent, changed);
  }, [setItems]);
  return <div className="feed-list">
    <header className="feed-heading"><h1>Bookmarks</h1><span className="eyebrow">Private</span></header>
    <div aria-busy={list.loading}>{list.items.map((item) => <div key={item.id}>
      <p className="bookmark-date">Saved {new Date(item.saved_at).toLocaleDateString()}</p>
      <FeedCard item={item.publication} onChanged={list.refresh} />
    </div>)}</div>
    {list.loading && !list.error && <PublicationListSkeleton count={list.items.length || list.cursor ? 2 : 3}
      label="Loading saved publications…" />}
    {list.error && <p role="alert" className="notice-error">{list.error}{" "}
      <button className="underline" onClick={list.cursor ? () => void list.loadMore() : list.refresh}>Retry</button>
    </p>}
    {!list.loading && !list.error && !list.items.length && <p className="list-status">
      {list.cursor ? "No available publications in this part of your shelf. Continue to see older saves." : "Your shelf is empty. Save a note or article to find it here."}
    </p>}
    <InfiniteScroll hasMore={!!list.cursor} loading={list.loading} error={list.error} loadMore={list.loadMore} />
    <button className="list-more" disabled={list.loading} onClick={list.refresh}>Refresh shelf</button>
  </div>;
}
