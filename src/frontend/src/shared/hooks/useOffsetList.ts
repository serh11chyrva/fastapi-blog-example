import { useEffect, useRef, useState } from "react";
import { api, errorMessage } from "../api/client";
type PageState<T> = {
  path: string | null;
  items: T[];
  loading: boolean;
  error: string;
  hasMore: boolean;
};
export function useOffsetList<T>(path: string | null, pageSize = 20) {
  const [state, setState] = useState<PageState<T>>({ path, items: [], loading: !!path, error: "", hasMore: false });
  const active = useRef<AbortController | null>(null);
  const busy = useRef(false);
  useEffect(() => {
    const controller = new AbortController();
    active.current = controller;
    busy.current = !!path;
    setState({ path, items: [], loading: !!path, error: "", hasMore: false });
    if (path) {
      const separator = path.includes("?") ? "&" : "?";
      api<T[]>(`${path}${separator}offset=0&limit=${pageSize}`, { signal: controller.signal })
        .then((items) => {
          if (!controller.signal.aborted)
            setState({ path, items, loading: false, error: "", hasMore: items.length === pageSize });
        })
        .catch((reason: unknown) => {
          if (!controller.signal.aborted)
            setState({ path, items: [], loading: false, error: errorMessage(reason), hasMore: false });
        })
        .finally(() => {
          if (!controller.signal.aborted)
            busy.current = false;
        });
    }
    return () => controller.abort();
  }, [path, pageSize]);
  async function loadMore() {
    if (!path || state.path !== path || !state.hasMore || busy.current || !active.current)
      return;
    const controller = active.current;
    busy.current = true;
    setState((value) => ({ ...value, loading: true, error: "" }));
    try {
      const separator = path.includes("?") ? "&" : "?";
      const items = await api<T[]>(`${path}${separator}offset=${state.items.length}&limit=${pageSize}`, { signal: controller.signal });
      if (!controller.signal.aborted)
        setState((value) => ({ path, items: [...value.items, ...items], loading: false, error: "", hasMore: items.length === pageSize }));
    }
    catch (reason) {
      if (!controller.signal.aborted)
        setState((value) => ({ ...value, loading: false, error: errorMessage(reason) }));
    }
    finally {
      if (!controller.signal.aborted)
        busy.current = false;
    }
  }
  return state.path === path
    ? { ...state, loadMore }
    : { path, items: [] as T[], loading: !!path, error: "", hasMore: false, loadMore };
}
