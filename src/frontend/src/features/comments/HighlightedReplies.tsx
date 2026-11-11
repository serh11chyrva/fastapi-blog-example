import { useEffect, useRef, useState } from "react";
import { ReplyThread } from "./ReplyThread";
import { useApp } from "../../app/AuthProvider";
import { api } from "../../shared/api/client";
import type { CursorPage, PostReply } from "../../shared/api/types";
import { itemId, mergeListItems } from "../../shared/hooks/listItems";
import { interactionEvent } from "../interactions/events";
import type { InteractionChange } from "../interactions/events";

export function HighlightedReplies({ postId }: { postId: string }) {
  const { user } = useApp();
  const marker = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);
  const [version, setVersion] = useState(0);
  const [items, setItems] = useState<PostReply[]>([]);
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    const element = marker.current;
    if (!element) return;
    if (!("IntersectionObserver" in window)) { setVisible(true); return; }
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
    }).then((page) => { if (!controller.signal.aborted) setItems(mergeListItems([], page.items, itemId)); })
      .catch(() => { if (!controller.signal.aborted) setItems([]); });
    return () => controller.abort();
  }, [visible, postId, user?.id, version]);

  return <div ref={marker}>
    {!!items.length && <aside className="highlighted-replies space-y-2" aria-label="Highlighted replies">
      <p>Top reply</p>
      {items.slice(0, expanded ? 2 : 1).map((item) => item.publication &&
        <ReplyThread key={`${user?.id ?? "anonymous"}:${item.id}`} comment={item} kind="micro_post" publicationId={postId}
          base={`/posts/${encodeURIComponent(postId)}/replies`}
          onUpdate={(updated) => setItems((previous) => previous.map((reply) => reply.id === updated.id
            ? { ...reply, ...updated } : reply))} />)}
      {items.length > 1 && <button type="button" className="text-sm underline" aria-expanded={expanded}
        onClick={() => setExpanded((value) => !value)}>{expanded ? "Hide additional reply" : "Show another reply"}</button>}
    </aside>}
  </div>;
}
