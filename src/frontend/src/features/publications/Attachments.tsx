import { useEffect, useState } from "react";
import { api, errorMessage } from "../../shared/api/client";
import type { Attachment, PublicationPreview } from "../../shared/api/types";
import { Icon } from "../../shared/ui/Icon";
import { embedSource } from "./embedSource";
import { MediaGallery } from "./MediaGallery";
import { PreviewCard } from "./PreviewCard";

const providerNames = { youtube: "YouTube", vimeo: "Vimeo", soundcloud: "SoundCloud", spotify: "Spotify", twitch: "Twitch" };

function Player({ item }: { item: Extract<Attachment, { type: "embed" }> }) {
  const source = embedSource(item);
  const [playing, setPlaying] = useState(false);
  const audio = item.provider === "spotify" || item.provider === "soundcloud";
  const provider = providerNames[item.provider];
  return <div className={`embed-card ${audio ? "audio-card" : "video-card"}`}>
    {playing && source ? <iframe className={audio ? "audio-frame" : "video-frame"} src={source} title={`${provider} player`}
      allow="encrypted-media; picture-in-picture; fullscreen" referrerPolicy="strict-origin-when-cross-origin" allowFullScreen />
      : <div className="embed-preview">
        <div className="embed-art"><Icon name={audio ? "music" : "play"} width={26} height={26} /></div>
        <div className="embed-copy"><span>{audio ? "Audio" : "Video"}</span><strong>{provider}</strong></div>
        {source && <button type="button" className="embed-play" aria-label={`Load ${provider} player`}
          onClick={() => setPlaying(true)}><Icon name="play" width={18} height={18} /></button>}
      </div>}
    <a className="embed-link" href={item.url} target="_blank" rel="noopener noreferrer">
      Open on {provider}<Icon name="external" width={14} height={14} />
    </a>
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
        case "hashtag": return <span className="attachment-tag" key={key}>#{item.tag}</span>;
        case "mention": return <span className="attachment-tag" title={item.user_id} key={key}>Account mention · {item.user_id.slice(-6)}</span>;
        case "embed": return <Player key={key} item={item} />;
        case "og_card":
          return <a key={key} href={item.url} target="_blank" rel="noopener noreferrer"
            className={`og-card ${item.image_url ? "has-thumbnail" : ""}`}>
            {item.image_url && <img src={item.image_url} alt="" loading="lazy" referrerPolicy="no-referrer" />}
            <div className="og-copy">
              <small>{item.site_name ?? new URL(item.url).hostname}<Icon name="external" width={13} height={13} /></small>
              <strong>{item.title}</strong>{item.description && <span>{item.description}</span>}
            </div>
          </a>;
        case "image": return null;
        default: return <a key={key} className="simple-attachment" href={item.url} target="_blank" rel="noopener noreferrer">
          <Icon name="link" width={15} height={15} />{item.type === "link" ? item.label || item.url : "Open video"}
          <Icon name="external" width={14} height={14} />
        </a>;
      }
    })}
    {current?.error && <p className="notice-error" role="alert">{current.error}{" "}
      <button type="button" className="text-link" onClick={() => setVersion((value) => value + 1)}>Retry</button>
    </p>}
  </div>;
}
