import { useEffect, useRef, useState } from "react";
import { api, errorMessage } from "../api/client";
import type { CursorPage } from "../api/types";

export function useCursorList<T extends { id: string }>(path: string) {
  const [items, setItems] = useState<T[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [version, setVersion] = useState(0);
  const active = useRef<AbortController | null>(null);
  const pending = useRef(false);
  const key = `${path}:${version}`;
  const activeKey = useRef(key);
  const pagePath = `${path}${path.includes("?") ? "&" : "?"}limit=20`;

  useEffect(() => {
    const controller = new AbortController();
    active.current = controller;
    activeKey.current = key;
    pending.current = true;
    setLoading(true);
    setError("");
    setItems([]);
    setCursor(null);
    api<CursorPage<T>>(pagePath, { signal: controller.signal })
      .then((page) => {
        if (!controller.signal.aborted) {
          setItems(page.items);
          setCursor(page.next_cursor);
        }
      })
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) setError(errorMessage(reason));
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          pending.current = false;
          setLoading(false);
        }
      });
    return () => controller.abort();
  }, [path, version]);

  async function loadMore() {
    const controller = active.current;
    if (!cursor || pending.current || !controller || activeKey.current !== key) return;
    pending.current = true;
    setLoading(true);
    setError("");
    try {
      const page = await api<CursorPage<T>>(`${pagePath}&cursor=${encodeURIComponent(cursor)}`, {
        signal: controller.signal,
      });
      if (!controller.signal.aborted) {
        setItems((previous) => {
          const seen = new Set(previous.map((item) => item.id));
          return [...previous, ...page.items.filter((item) => !seen.has(item.id))];
        });
        setCursor(page.next_cursor);
      }
    } catch (reason) {
      if (!controller.signal.aborted) setError(errorMessage(reason));
    } finally {
      if (!controller.signal.aborted) {
        pending.current = false;
        setLoading(false);
      }
    }
  }

  return { items, setItems, loading, error, cursor, loadMore, refresh: () => setVersion((value) => value + 1) };
}
