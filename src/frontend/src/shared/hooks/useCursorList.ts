import { useCallback, useEffect, useRef, useState } from "react";
import type { SetStateAction } from "react";
import { api, errorMessage } from "../api/client";
import type { CursorPage } from "../api/types";
import { itemId, mergeListItems } from "./listItems";

type PageState<T> = { key: string; items: T[]; cursor: string | null; loading: boolean; error: string };

export function useCursorList<T extends { id: string }>(
  path: string, identify: (item: T) => string = itemId, resetKey: string | number = 0,
) {
  const [version, setVersion] = useState(0);
  const key = JSON.stringify([path, version, resetKey]);
  const [state, setState] = useState<PageState<T>>({ key: "", items: [], cursor: null, loading: true, error: "" });
  const active = useRef<{ key: string; controller: AbortController; busy: boolean; visited: Set<string> } | null>(null);
  const pagePath = `${path}${path.includes("?") ? "&" : "?"}limit=20`;

  useEffect(() => {
    const request = { key, controller: new AbortController(), busy: true, visited: new Set<string>() };
    active.current = request;
    setState({ key, items: [], cursor: null, loading: true, error: "" });
    api<CursorPage<T>>(pagePath, { signal: request.controller.signal })
      .then((page) => {
        if (!request.controller.signal.aborted)
          setState({ key, items: mergeListItems([], page.items, identify), cursor: page.next_cursor, loading: false, error: "" });
      })
      .catch((reason: unknown) => {
        if (!request.controller.signal.aborted)
          setState((value) => ({ ...value, loading: false, error: errorMessage(reason) }));
      })
      .finally(() => { request.busy = false; });
    return () => request.controller.abort();
  }, [key, pagePath]);

  async function loadMore() {
    const request = active.current;
    if (state.key !== key || !state.cursor || !request || request.key !== key || request.busy) return;
    const cursor = state.cursor;
    request.busy = true;
    setState((value) => ({ ...value, loading: true, error: "" }));
    try {
      const page = await api<CursorPage<T>>(`${pagePath}&cursor=${encodeURIComponent(cursor)}`, {
        signal: request.controller.signal,
      });
      if (request.controller.signal.aborted) return;
      request.visited.add(cursor);
      const repeated = page.next_cursor !== null && request.visited.has(page.next_cursor);
      setState((previous) => ({
        key, items: mergeListItems(previous.items, page.items, identify),
        cursor: repeated ? cursor : page.next_cursor, loading: false,
        error: repeated ? "Pagination did not advance. Retry or refresh this list." : "",
      }));
    } catch (reason) {
      if (!request.controller.signal.aborted)
        setState((value) => ({ ...value, loading: false, error: errorMessage(reason) }));
    } finally { request.busy = false; }
  }

  const setItems = useCallback((update: SetStateAction<T[]>) => {
    setState((value) => value.key !== key ? value : {
      ...value, items: typeof update === "function" ? update(value.items) : update,
    });
  }, [key]);
  const current = state.key === key ? state : { key, items: [] as T[], cursor: null, loading: true, error: "" };
  return { ...current, setItems, loadMore, refresh: () => setVersion((value) => value + 1) };
}
