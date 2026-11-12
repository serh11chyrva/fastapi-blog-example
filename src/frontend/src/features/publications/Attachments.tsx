import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { hashtagHref } from "../../shared/text/hashtags";
import { api, errorMessage } from "../../shared/api/client";
import type { Attachment, PublicationPreview } from "../../shared/api/types";
import { Icon } from "../../shared/ui/Icon";
import { ResolvedLink } from "./ResolvedLink";
import { MediaGallery } from "./MediaGallery";
import { publicationStateEvent } from "../interactions/events";
import { PreviewCard } from "./PreviewCard";

function reference(item: Attachment): string | null {
  if (item.type === "article") return `article:${item.article_id.toLowerCase()}`;
  if (item.type === "post") return `micro_post:${item.post_id.toLowerCase()}`;
  return null;
}

export function Attachments({ items, editable = false }: { items: Attachment[]; editable?: boolean }) {
  const query = new URLSearchParams();
  for (const ref of new Set(items.map(reference))) {
    if (ref) query.append("ref", ref);
  }
  const params = query.toString();
  const [request, setRequest] = useState<{ params: string; cards: PublicationPreview[]; error?: string }>();
  const [version, setVersion] = useState(0);
  useEffect(() => {
    function changed() { setVersion((value) => value + 1); }
    window.addEventListener(publicationStateEvent, changed);
    return () => window.removeEventListener(publicationStateEvent, changed);
  }, []);

  useEffect(() => {
    if (!params) return;
    const controller = new AbortController();
    api<PublicationPreview[]>(`/publications/previews?${params}`, { signal: controller.signal, cache: "no-store" })
      .then((cards) => { if (!controller.signal.aborted) setRequest({ params, cards }); })
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) setRequest({ params, cards: [], error: errorMessage(reason) });
      });
    return () => controller.abort();
  }, [params, version]);

  if (!items.length) return null;
  const current = request?.params === params ? request : undefined;
  const blocks: (Attachment | Extract<Attachment, { type: "image" }>[])[] = [];
  for (const item of items) {
    const last = blocks.at(-1);
    if (item.type !== "image") blocks.push(item);
    else if (Array.isArray(last)) last.push(item);
    else blocks.push([item]);
  }

  return <div className="attachment-stack">
    {blocks.map((item, index) => {
      if (Array.isArray(item)) return <MediaGallery key={`${index}:gallery`} images={item} />;
      const ref = reference(item);
      const card = current?.cards.find((value) => `${value.kind}:${value.id}` === ref);
      const key = `${index}:${"url" in item ? item.url : item.type}`;
      switch (item.type) {
        case "article":
        case "post":
          return card ? <PreviewCard key={key} item={card} /> : <p key={key} className="attachment-placeholder">
            {current ? "Publication unavailable" : "Loading publication…"}
          </p>;
        case "hashtag": return editable ? <span className="attachment-tag hashtag" key={key}>#{item.tag}</span>
          : <Link className="attachment-tag hashtag" key={key} to={hashtagHref(item.tag)}>#{item.tag}</Link>;
        case "mention": return <span className="attachment-tag" title={item.user_id} key={key}>Account mention · {item.user_id.slice(-6)}</span>;
        case "embed":
        case "og_card":
        case "link": return <ResolvedLink key={key} item={item} />;
        case "image": return null;
        default: return <a key={key} className="simple-attachment" href={item.url} target="_blank" rel="noopener noreferrer">
          <Icon name="link" width={15} height={15} />Open video
          <Icon name="external" width={14} height={14} />
        </a>;
      }
    })}
    {current?.error && <p className="notice-error" role="alert">{current.error}{" "}
      <button type="button" className="text-link" onClick={() => setVersion((value) => value + 1)}>Retry</button>
    </p>}
  </div>;
}
