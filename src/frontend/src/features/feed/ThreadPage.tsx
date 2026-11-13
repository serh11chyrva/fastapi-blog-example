import { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useApp } from "../../app/AuthProvider";
import { usePageTitle } from "../../app/usePageTitle";
import { api, errorMessage } from "../../shared/api/client";
import type { AuthorThreadPage } from "../../shared/api/types";
import { itemId, mergeListItems } from "../../shared/hooks/listItems";
import { EmptyState } from "../../shared/ui/EmptyState";
import { PublicationListSkeleton } from "../publications/PublicationSkeleton";
import { FeedCard } from "./FeedCard";
import { ThreadPartCard } from "./ThreadCard";

export function ThreadPage() {
  const { postId = "" } = useParams();
  const { user } = useApp();
  return <ThreadContent key={`${postId}:${user?.id ?? "anonymous"}`} postId={postId} />;
}

function ThreadContent({ postId }: { postId: string }) {
  const [page, setPage] = useState<AuthorThreadPage | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [version, setVersion] = useState(0);
  const active = useRef<{ controller: AbortController; busy: boolean; visited: Set<string> } | null>(null);
  const path = `/posts/${encodeURIComponent(postId)}/thread?limit=20`;
  const refresh = () => setVersion((value) => value + 1);

  useEffect(() => {
    const request = { controller: new AbortController(), busy: true, visited: new Set<string>() };
    active.current = request;
    setPage(null); setError(""); setLoading(true);
    api<AuthorThreadPage>(path, { signal: request.controller.signal, cache: "no-store" })
      .then((value) => { if (!request.controller.signal.aborted) setPage(value); })
      .catch((reason: unknown) => { if (!request.controller.signal.aborted) setError(errorMessage(reason)); })
      .finally(() => { request.busy = false; if (!request.controller.signal.aborted) setLoading(false); });
    return () => request.controller.abort();
  }, [path, version]);

  async function loadMore() {
    const request = active.current;
    const cursor = page?.next_cursor;
    if (!request || request.busy || !cursor) return;
    request.busy = true; setLoading(true); setError("");
    try {
      const next = await api<AuthorThreadPage>(`${path}&cursor=${encodeURIComponent(cursor)}`, {
        signal: request.controller.signal, cache: "no-store",
      });
      if (request.controller.signal.aborted) return;
      request.visited.add(cursor);
      if (next.next_cursor && request.visited.has(next.next_cursor)) {
        setError("Pagination did not advance. Retry or refresh this thread.");
        return;
      }
      setPage((previous) => ({ ...next, items: mergeListItems(previous?.items ?? [], next.items, itemId) }));
    } catch (reason) {
      if (!request.controller.signal.aborted) setError(errorMessage(reason));
    } finally {
      request.busy = false;
      if (!request.controller.signal.aborted) setLoading(false);
    }
  }

  usePageTitle(page ? `Thread by ${page.root.authors[0]?.display_name ?? "Unknown author"}` : "Author thread");
  return <section className="post-detail full-thread" aria-label="Author thread">
    <header className="thread-heading"><h1>Thread</h1>
      <Link className="text-link" to={`/posts/${postId}#replies`}>Open discussion</Link>
    </header>
    {page && <div className="thread-parts" aria-busy={loading}>
      <FeedCard item={page.root} onChanged={refresh} showContext={false} />
      {page.items.map((part) => <div key={part.id}><ThreadPartCard part={part} onChanged={refresh} /></div>)}
    </div>}
    {loading && <PublicationListSkeleton count={page ? 2 : 3} label="Loading thread…" />}
    {error && <div className="thread-status" role="alert">
      {!page ? <EmptyState title="Thread unavailable" body={error} /> : <p className="notice-error">{error}</p>}
      <button className="button-secondary" onClick={page?.next_cursor ? () => void loadMore() : refresh}>Retry</button>
    </div>}
    {page?.next_cursor && !error && <button className="button-secondary thread-load-more" disabled={loading}
      onClick={() => void loadMore()}>Load more</button>}
  </section>;
}
