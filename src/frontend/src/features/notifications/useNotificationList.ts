import { useCallback, useEffect, useRef, useState } from "react";
import { api, errorMessage } from "../../shared/api/client";
import type { CursorPage, NotificationItem } from "../../shared/api/types";
import { useNotifications } from "./NotificationsProvider";

type InboxState = {
  items: NotificationItem[];
  cursor: string | null;
  loading: boolean;
  loaded: boolean;
  error: string;
  failedOperation: "refresh" | "more";
  refreshAvailable: boolean;
};

export function useNotificationList() {
  const { subscribeToPoll } = useNotifications();
  const [state, setState] = useState<InboxState>({
    items: [], cursor: null, loading: true, loaded: false, error: "",
    failedOperation: "refresh", refreshAvailable: false,
  });
  const current = useRef(state);
  const mounted = useRef(false);
  const request = useRef<AbortController | null>(null);
  const visited = useRef(new Set<string>());
  const atTop = useRef(true);

  const update = useCallback((change: (value: InboxState) => InboxState) => {
    current.current = change(current.current);
    setState(current.current);
  }, []);

  const refresh = useCallback(async (background = false) => {
    if (!mounted.current || (background && request.current)) return;
    request.current?.abort();
    const controller = new AbortController();
    request.current = controller;
    update((value) => ({ ...value, loading: true, error: "" }));
    try {
      const page = await api<CursorPage<NotificationItem>>("/me/notifications?limit=20", {
        signal: controller.signal,
      });
      if (controller.signal.aborted || request.current !== controller) return;
      visited.current.clear();
      update(() => ({
        items: page.items, cursor: page.next_cursor, loading: false, loaded: true,
        error: "", failedOperation: "refresh", refreshAvailable: false,
      }));
    } catch (reason) {
      if (!controller.signal.aborted && request.current === controller)
        update((value) => ({ ...value, loading: false, error: errorMessage(reason), failedOperation: "refresh" }));
    } finally {
      if (request.current === controller) request.current = null;
    }
  }, [update]);

  const loadMore = useCallback(async () => {
    const cursor = current.current.cursor;
    if (!mounted.current || request.current || !cursor) return;
    const controller = new AbortController();
    request.current = controller;
    update((value) => ({ ...value, loading: true, error: "" }));
    try {
      const page = await api<CursorPage<NotificationItem>>(
        `/me/notifications?limit=20&cursor=${encodeURIComponent(cursor)}`, { signal: controller.signal },
      );
      if (controller.signal.aborted || request.current !== controller) return;
      visited.current.add(cursor);
      const repeated = page.next_cursor !== null && visited.current.has(page.next_cursor);
      update((value) => {
        const rows = new Map(value.items.map((item) => [item.id, item]));
        for (const item of page.items) rows.set(item.id, item);
        return {
          ...value, items: [...rows.values()], loading: false,
          cursor: repeated ? cursor : page.next_cursor, failedOperation: "more",
          error: repeated ? "Pagination did not advance. Refresh this inbox before continuing." : "",
        };
      });
    } catch (reason) {
      if (!controller.signal.aborted && request.current === controller)
        update((value) => ({ ...value, loading: false, error: errorMessage(reason), failedOperation: "more" }));
    } finally {
      if (request.current === controller) request.current = null;
    }
  }, [update]);

  useEffect(() => {
    mounted.current = true;
    window.scrollTo({ top: 0, behavior: "auto" });
    atTop.current = window.scrollY < 120;
    void refresh();
    const unsubscribe = subscribeToPoll(() => {
      if (atTop.current) void refresh(true);
      else update((value) => ({ ...value, refreshAvailable: true }));
    });
    function scrolled() {
      const returnedToTop = !atTop.current && window.scrollY < 120;
      atTop.current = window.scrollY < 120;
      if (returnedToTop && current.current.refreshAvailable && document.visibilityState === "visible")
        void refresh(true);
    }
    window.addEventListener("scroll", scrolled, { passive: true });
    return () => {
      mounted.current = false;
      request.current?.abort();
      request.current = null;
      unsubscribe();
      window.removeEventListener("scroll", scrolled);
    };
  }, [refresh, subscribeToPoll, update]);

  return { ...state, refresh, loadMore };
}
