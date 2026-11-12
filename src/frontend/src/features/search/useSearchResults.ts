import { useCallback, useEffect, useRef, useState } from "react";
import { api, errorMessage } from "../../shared/api/client";
import type { CursorPage } from "../../shared/api/types";

type ResultState<T> = { key: string; items: T[]; cursor: string | null; loading: boolean; error: string };
type ActiveRequest = { key: string; controller: AbortController; busy: boolean; visited: Set<string> };

export function useSearchResults<T>(path: string | null, initialLimit: number, moreLimit: number, identify: (item: T) => string) {
  const [version, setVersion] = useState(0);
  const key = JSON.stringify([path, version]);
  const [state, setState] = useState<ResultState<T>>({ key: "", items: [], cursor: null, loading: false, error: "" });
  const active = useRef<ActiveRequest | null>(null);
  useEffect(() => {
    const request = { key, controller: new AbortController(), busy: !!path, visited: new Set<string>() };
    active.current = request;
    setState({ key, items: [], cursor: null, loading: !!path, error: "" });
    if (path) {
      api<CursorPage<T>>(`${path}&limit=${initialLimit}`, { signal: request.controller.signal, cache: "no-store" })
        .then((page) => {
          if (!request.controller.signal.aborted)
            setState({ key, items: page.items, cursor: page.next_cursor, loading: false, error: "" });
        })
        .catch((reason: unknown) => {
          if (!request.controller.signal.aborted)
            setState((previous) => ({ ...previous, loading: false, error: errorMessage(reason) }));
        })
        .finally(() => { request.busy = false; });
    }
    return () => request.controller.abort();
  }, [key, path, initialLimit]);

  async function loadMore() {
    const request = active.current;
    if (!path || state.key !== key || !state.cursor || !request || request.key !== key || request.busy) return;
    const cursor = state.cursor;
    request.busy = true;
    setState((previous) => ({ ...previous, loading: true, error: "" }));
    try {
      const page = await api<CursorPage<T>>(`${path}&limit=${moreLimit}&cursor=${encodeURIComponent(cursor)}`, {
        signal: request.controller.signal, cache: "no-store",
      });
      if (request.controller.signal.aborted) return;
      request.visited.add(cursor);
      if (page.next_cursor && request.visited.has(page.next_cursor)) throw new Error("Search pagination did not advance. Retry or refresh.");
      setState((previous) => {
        const items = new Map(previous.items.map((item) => [identify(item), item]));
        for (const item of page.items) items.set(identify(item), item);
        return { key, items: [...items.values()], cursor: page.next_cursor, loading: false, error: "" };
      });
    } catch (reason) {
      if (!request.controller.signal.aborted)
        setState((previous) => ({ ...previous, loading: false, error: errorMessage(reason) }));
    } finally { request.busy = false; }
  }

  const refresh = useCallback(() => setVersion((value) => value + 1), []);
  const current = state.key === key ? state : { key, items: [] as T[], cursor: null, loading: !!path, error: "" };
  return { ...current, loadMore, refresh, retry: () => current.items.length && current.cursor ? loadMore() : refresh() };
}
