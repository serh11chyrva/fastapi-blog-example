import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { useApp } from "../../app/AuthProvider";
import { api } from "../../shared/api/client";
import type { CursorPage, PostReply } from "../../shared/api/types";
import { interactionEvent } from "../interactions/events";
import type { InteractionChange } from "../interactions/events";

export function HighlightedReplies({ postId, openDiscussion }: { postId: string; openDiscussion: () => void }) {
  const { user } = useApp();
  const marker = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);
  const [version, setVersion] = useState(0);
  const [items, setItems] = useState<PostReply[]>([]);
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    const element = marker.current;
    if (!element) return;
    const observer = new IntersectionObserver(([entry]) => {
      if (entry?.isIntersecting) {
        setVisible(true);
        observer.disconnect();
      }
    }, { rootMargin: "120px" });
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (!visible) return;
    function changed(event: Event) {
      const detail = (event as CustomEvent<InteractionChange>).detail;
      if (detail.kind === "micro_post" && detail.id === postId) setVersion((value) => value + 1);
    }
    window.addEventListener(interactionEvent, changed);
    return () => window.removeEventListener(interactionEvent, changed);
  }, [visible, postId]);

  useEffect(() => {
    if (!visible) return;
    const controller = new AbortController();
    api<CursorPage<PostReply>>(`/posts/${encodeURIComponent(postId)}/replies?sort=most_liked&limit=2`, {
      signal: controller.signal, cache: "no-store",
    }).then((page) => { if (!controller.signal.aborted) setItems(page.items); })
      .catch(() => { if (!controller.signal.aborted) setItems([]); });
    return () => controller.abort();
  }, [visible, postId, user?.id, version]);

  return <div ref={marker}>
    {!!items.length && <aside className="mt-4 space-y-3 rounded bg-neutral-50 p-4" aria-label="Highlighted replies">
      <p className="text-xs font-semibold uppercase tracking-wide text-neutral-500">Top reply</p>
      {items.slice(0, expanded ? 2 : 1).map((item) => <div className="space-y-1 text-sm" key={item.id}>
        {item.author && <Link to={`/@${item.author.username}`} className="font-semibold">{item.author.display_name}</Link>}
        <p className="line-clamp-3 whitespace-pre-wrap break-words">{item.text}</p>
        <span className="mr-3 text-neutral-500">♡ {item.likes_count}</span>
        <button type="button" className="underline" onClick={openDiscussion}>Open discussion</button>
      </div>)}
      {items.length > 1 && <button type="button" className="text-sm underline" aria-expanded={expanded}
        onClick={() => setExpanded((value) => !value)}>{expanded ? "Hide additional reply" : "Show another reply"}</button>}
    </aside>}
  </div>;
}
