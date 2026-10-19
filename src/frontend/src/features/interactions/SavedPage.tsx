import { useEffect } from "react";
import { useApp } from "../../app/AuthProvider";
import type { SavedPublication } from "../../shared/api/types";
import { useCursorList } from "../../shared/hooks/useCursorList";
import { FeedCard } from "../feed/FeedCard";
import { interactionEvent } from "./events";
import type { InteractionChange } from "./events";

export function SavedPage() {
  const { user } = useApp();
  return <SavedList key={user?.id} />;
}

function SavedList() {
  const list = useCursorList<SavedPublication>("/me/saved");
  const { setItems } = list;
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
  return <div className="space-y-5">
    <header><p className="eyebrow">Your reading shelf</p><h1 className="page-title">Saved</h1>
      <p className="mt-2 text-sm text-neutral-500">Notes and articles to return to. Only you can see this list.</p>
    </header>
    {list.items.map((item) => <div key={item.id}>
      <p className="mb-2 text-xs text-neutral-400">Saved {new Date(item.saved_at).toLocaleDateString()}</p>
      <FeedCard item={item.publication} onChanged={list.refresh} />
    </div>)}
    {list.loading && <p role="status">Loading saved publications…</p>}
    {list.error && <p role="alert" className="notice-error">{list.error}{" "}
      <button className="underline" onClick={list.cursor ? () => void list.loadMore() : list.refresh}>Retry</button>
    </p>}
    {!list.loading && !list.error && !list.items.length && <p className="surface p-6 text-sm text-neutral-500">
      {list.cursor ? "No available publications in this part of your shelf. Continue to see older saves." : "Your shelf is empty. Save a note or article to find it here."}
    </p>}
    {list.cursor && <button className="button-secondary w-full" disabled={list.loading} onClick={() => void list.loadMore()}>Load more saves</button>}
    <button className="button-quiet" disabled={list.loading} onClick={list.refresh}>Refresh shelf</button>
  </div>;
}
