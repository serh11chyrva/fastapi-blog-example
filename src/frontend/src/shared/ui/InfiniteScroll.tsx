import { useEffect, useRef } from "react";

export function InfiniteScroll({ hasMore, loading, error, loadMore }: {
  hasMore: boolean; loading: boolean; error: string; loadMore: () => Promise<void>;
}) {
  const marker = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!hasMore || loading || error || !marker.current || !("IntersectionObserver" in window)) return;
    let requested = false;
    const observer = new IntersectionObserver(([entry]) => {
      if (!requested && entry?.isIntersecting) {
        requested = true;
        void loadMore();
      }
    }, { rootMargin: "400px" });
    observer.observe(marker.current);
    return () => observer.disconnect();
  }, [hasMore, loading, error, loadMore]);
  return <div ref={marker} className="infinite-scroll-marker">
    {hasMore && !("IntersectionObserver" in window) && <button type="button" disabled={loading}
      onClick={() => void loadMore()}>Load more</button>}
  </div>;
}
