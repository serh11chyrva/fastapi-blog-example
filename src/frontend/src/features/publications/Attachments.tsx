import { useEffect, useState } from "react";
import { api, errorMessage } from "../../shared/api/client";
import type { Attachment, PublicationPreview } from "../../shared/api/types";
import { embedSource } from "./embedSource";
import { PreviewCard } from "./PreviewCard";

function Player({ item }: { item: Extract<Attachment, { type: "embed" }> }) {
  const source = embedSource(item);
  const [playing, setPlaying] = useState(false);
  const audio = item.provider === "spotify" || item.provider === "soundcloud";
  return <div className="space-y-2 rounded border border-neutral-200 p-3 text-sm">
    {source && (playing
      ? <iframe className={`w-full rounded ${audio ? "h-40" : "aspect-video"}`} src={source}
          title={`${item.provider} player`} allow="encrypted-media; picture-in-picture; fullscreen"
          referrerPolicy="strict-origin-when-cross-origin" allowFullScreen />
      : <button type="button" className="button-secondary mr-3" onClick={() => setPlaying(true)}>
          Load {item.provider} player
        </button>)}
    <a className="underline" href={item.url} target="_blank" rel="noopener noreferrer">Open on {item.provider} ↗</a>
  </div>;
}

function reference(item: Attachment): string | null {
  if (item.type === "article") return `article:${item.article_id.toLowerCase()}`;
  if (item.type === "post") return `micro_post:${item.post_id.toLowerCase()}`;
  return null;
}

export function Attachments({ items }: { items: Attachment[] }) {
  const query = new URLSearchParams();
  for (const ref of new Set(items.map(reference))) {
    if (ref) query.append("ref", ref);
  }
  const params = query.toString();
  const [request, setRequest] = useState<{ params: string; cards: PublicationPreview[]; error?: string }>();
  const [version, setVersion] = useState(0);
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
  return <div className="mt-4 space-y-3">
    {items.map((item, index) => {
      const ref = reference(item);
      const card = current?.cards.find((value) => `${value.kind}:${value.id}` === ref);
      return <div key={`${index}:${"url" in item ? item.url : item.type}`} className="min-w-0 break-words">
        {item.type === "image" ? <img className="max-h-[32rem] w-full bg-neutral-50 object-contain" src={item.url} alt={item.alt} loading="lazy" />
          : item.type === "article" || item.type === "post" ? (card ? <PreviewCard item={card} />
            : <p className="rounded border border-neutral-200 p-3 text-sm text-neutral-500">
                {current ? "Publication unavailable" : "Loading publication…"}
              </p>)
          : item.type === "hashtag" ? <span className="pill">#{item.tag}</span>
          : item.type === "mention" ? <span className="pill" title={item.user_id}>Account mention · {item.user_id.slice(-6)}</span>
          : item.type === "embed" ? <Player item={item} />
          : item.type === "og_card" ? <a href={item.url} target="_blank" rel="noopener noreferrer" className="block overflow-hidden border border-neutral-200">
            {item.image_url && <img src={item.image_url} alt="" loading="lazy" referrerPolicy="no-referrer" className="max-h-52 w-full object-cover" />}
            <span className="block p-4"><strong className="block">{item.title}</strong>
              <span className="mt-1 block text-sm text-neutral-600">{item.description}</span>
              <span className="mt-2 block text-xs text-neutral-500">{item.site_name || item.url} ↗</span>
            </span>
          </a>
          : <a className="block border border-neutral-200 p-3 text-sm underline" href={item.url} target="_blank" rel="noopener noreferrer">
            {item.type === "link" ? item.label || item.url : "Open video ↗"}
          </a>}
      </div>;
    })}
    {current?.error && <p className="text-sm" role="alert">{current.error}{" "}
      <button type="button" className="underline" onClick={() => setVersion((value) => value + 1)}>Retry</button>
    </p>}
  </div>;
}
