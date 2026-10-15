import { useEffect, useRef, useState } from "react";
import { api, errorMessage } from "../../shared/api/client";
import type { Feed } from "../../shared/api/types";
export function useFeed(path: string, kind: string, refreshKey: number) {
  const [feed, setFeed] = useState<Feed>({ items: [], next_cursor: null });
  const [busy, setBusy] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState("");
  const active = useRef<AbortController | null>(null);
  const queryKey = `${path}:${kind}:${refreshKey}`;
  const activeKey = useRef(queryKey);
  const moreBusy = useRef(false);
  useEffect(() => {
    const controller = new AbortController();
    active.current = controller;
    activeKey.current = queryKey;
    moreBusy.current = false;
    setBusy(true);
    setLoadingMore(false);
    setError("");
    setFeed({ items: [], next_cursor: null });
    api<Feed>(`${path}?kind=${kind}&limit=20`, { signal: controller.signal })
      .then((value) => {
        if (!controller.signal.aborted)
          setFeed(value);
      })
      .catch((reason: unknown) => {
        if (!controller.signal.aborted)
          setError(errorMessage(reason));
      })
      .finally(() => {
        if (!controller.signal.aborted)
          setBusy(false);
      });
    return () => controller.abort();
  }, [path, kind, refreshKey]);
  async function loadMore() {
    if (activeKey.current !== queryKey || !feed.next_cursor || moreBusy.current || busy || !active.current)
      return;
    const controller = active.current;
    moreBusy.current = true;
    setLoadingMore(true);
    setError("");
    try {
      const next = await api<Feed>(`${path}?kind=${kind}&limit=20&cursor=${encodeURIComponent(feed.next_cursor)}`, { signal: controller.signal });
      if (!controller.signal.aborted)
        setFeed((value) => ({ items: [...value.items, ...next.items], next_cursor: next.next_cursor }));
    }
    catch (reason) {
      if (!controller.signal.aborted)
        setError(errorMessage(reason));
    }
    finally {
      if (!controller.signal.aborted) {
        moreBusy.current = false;
        setLoadingMore(false);
      }
    }
  }
  return { feed, busy, error, loadMore, loadingMore };
}
