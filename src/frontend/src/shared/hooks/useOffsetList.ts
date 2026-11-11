import { useEffect, useRef, useState } from "react";
import { api, errorMessage } from "../api/client";
import { itemId, mergeListItems } from "./listItems";

type PageState<T> = {
  key: string; items: T[]; loading: boolean; error: string; hasMore: boolean; offset: number;
};

export function useOffsetList<T extends { id: string }>(path: string | null, pageSize = 20, resetKey = "") {
  const key = JSON.stringify([path, pageSize, resetKey]);
  const [version, setVersion] = useState(0);
  const requestKey = `${key}:${version}`;
  const [state, setState] = useState<PageState<T>>({ key: "", items: [], loading: !!path, error: "", hasMore: false, offset: 0 });
  const active = useRef<{ key: string; controller: AbortController; busy: boolean } | null>(null);

  useEffect(() => {
    const request = { key: requestKey, controller: new AbortController(), busy: !!path };
    active.current = request;
    setState({ key: requestKey, items: [], loading: !!path, error: "", hasMore: false, offset: 0 });
    if (path) {
      const separator = path.includes("?") ? "&" : "?";
      api<T[]>(`${path}${separator}offset=0&limit=${pageSize}`, { signal: request.controller.signal })
        .then((items) => {
          if (!request.controller.signal.aborted)
            setState({ key: requestKey, items: mergeListItems([], items, itemId), loading: false,
              error: "", hasMore: items.length === pageSize, offset: items.length });
        })
        .catch((reason: unknown) => {
          if (!request.controller.signal.aborted)
            setState((value) => ({ ...value, loading: false, error: errorMessage(reason) }));
        })
        .finally(() => { request.busy = false; });
    }
    return () => request.controller.abort();
  }, [requestKey, path, pageSize]);

  async function loadMore() {
    const request = active.current;
    if (!path || state.key !== requestKey || !state.hasMore || !request || request.key !== requestKey || request.busy) return;
    request.busy = true;
    setState((value) => ({ ...value, loading: true, error: "" }));
    try {
      const separator = path.includes("?") ? "&" : "?";
      const items = await api<T[]>(`${path}${separator}offset=${state.offset}&limit=${pageSize}`, {
        signal: request.controller.signal,
      });
      if (!request.controller.signal.aborted)
        setState((value) => ({ ...value, items: mergeListItems(value.items, items, itemId),
          offset: value.offset + items.length, loading: false, error: "", hasMore: items.length === pageSize }));
    } catch (reason) {
      if (!request.controller.signal.aborted)
        setState((value) => ({ ...value, loading: false, error: errorMessage(reason) }));
    } finally { request.busy = false; }
  }
  const current = state.key === requestKey ? state
    : { key: requestKey, items: [] as T[], loading: !!path, error: "", hasMore: false, offset: 0 };
  return { ...current, path, loadMore, refresh: () => setVersion((value) => value + 1) };
}
