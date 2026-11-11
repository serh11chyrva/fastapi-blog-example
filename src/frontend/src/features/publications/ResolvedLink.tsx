import { useEffect, useRef, useState } from "react";
import type { Attachment } from "../../shared/api/types";
import { Icon } from "../../shared/ui/Icon";
import { embedSource } from "./embedSource";
import { useLinkResolution } from "./useLinkResolution";

type UrlAttachment = Extract<Attachment, { type: "embed" | "og_card" | "link" }>;

export function ResolvedLink({ item }: { item: UrlAttachment }) {
  const marker = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);
  const [failed, setFailed] = useState(false);
  useEffect(() => setFailed(false), [item.url]);
  useEffect(() => {
    const observer = new IntersectionObserver(([entry]) => {
      if (entry?.isIntersecting) { setVisible(true); observer.disconnect(); }
    }, { rootMargin: "200px" });
    if (marker.current) observer.observe(marker.current);
    return () => observer.disconnect();
  }, []);
  const result = useLinkResolution(item.url, visible);
  const resolved = result?.attachment;
  const source = resolved?.type === "embed" && result?.player_url && embedSource(resolved)
    ? result.player_url : null;
  const card = result?.status !== "ready" && item.type === "og_card" ? item
    : result?.card ?? (item.type === "og_card" ? item : null);
  const hostname = new URL(item.url).hostname;
  const audio = resolved?.type === "embed" && ["spotify", "soundcloud"].includes(resolved.provider);
  return <div ref={marker} className="resolved-link">
    {visible && source && !failed ? <div className={`embed-card ${audio ? "audio-card" : "video-card"}`}>
      <iframe className={audio ? "audio-frame" : "video-frame"} src={source}
        title={card?.title || `${resolved?.type === "embed" ? resolved.provider : hostname} player`}
        allow="encrypted-media; picture-in-picture; fullscreen" referrerPolicy="strict-origin-when-cross-origin"
        allowFullScreen onError={() => setFailed(true)} />
      <a className="embed-link" href={item.url} target="_blank" rel="noopener noreferrer">Open original<Icon name="external" /></a>
    </div> : <a href={item.url} target="_blank" rel="noopener noreferrer" className={`og-card ${card?.image_url ? "has-thumbnail" : ""}`}>
      {card?.image_url && <img key={card.image_url} src={card.image_url} alt="" loading="lazy" referrerPolicy="no-referrer" onError={(event) => { event.currentTarget.hidden = true; }} />}
      <div className="og-copy">
        <small>{card?.site_name || hostname}<Icon name="external" width={13} height={13} /></small>
        <strong>{card?.title || (item.type === "link" ? item.label : null) || hostname}</strong>
        {card?.description && <span>{card.description}</span>}
      </div>
    </a>}
  </div>;
}
