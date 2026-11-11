import { useApp } from "../../app/AuthProvider";
import type { FeedItem } from "../../shared/api/types";
import { useCursorList } from "../../shared/hooks/useCursorList";

function feedKey(item: FeedItem) { return `${item.kind}:${item.id}`; }

export function useFeed(path: string, kind: string, refreshKey: number) {
  const { user } = useApp();
  const list = useCursorList<FeedItem>(`${path}?kind=${encodeURIComponent(kind)}`, feedKey,
    `${refreshKey}:${user?.id ?? "anonymous"}`);
  return {
    feed: { items: list.items, next_cursor: list.cursor }, busy: list.loading && list.items.length === 0 && !list.cursor,
    loadingMore: list.loading, error: list.error, loadMore: list.loadMore,
    retry: list.cursor ? list.loadMore : list.refresh,
  };
}
