import { useState } from "react";
import { api, errorMessage } from "../../shared/api/client";
import type { Article, Attachment, MicroPost } from "../../shared/api/types";
import { embedSource } from "./embedSource";

type LinkCard = Extract<Attachment, { type: "og_card" }>;
const providers = ["youtube", "vimeo", "spotify", "soundcloud"] as const;

async function publicationReference(url: URL): Promise<Attachment> {
  if (url.origin !== window.location.origin) throw new Error("Use a link to a publication on this site.");
  const parts = url.pathname.split("/").filter(Boolean);
  if (parts.length !== 2) throw new Error("Use the link to a post or article.");
  const [section, id] = parts;
  if ((section === "posts" || section === "articles") && /^[0-9a-f]{24}$/i.test(id)) {
    const result = await api<MicroPost | Article>(`/${section}/${id}`);
    if (result.kind === "article" && result.status !== "published") throw new Error("This article is unavailable.");
    return result.kind === "article" ? { type: "article", article_id: result.id } : { type: "post", post_id: result.id };
  }
  const username = decodeURIComponent(section).replace(/^@/, "");
  const result = await api<MicroPost | Article>(`/publications/${encodeURIComponent(username)}/${id}`);
  return result.kind === "article" ? { type: "article", article_id: result.id } : { type: "post", post_id: result.id };
}

export function AttachmentComposer({ onAdd, disabled = false, allowQuote = true }: {
  onAdd: (attachment: Attachment) => void;
  disabled?: boolean;
  allowQuote?: boolean;
}) {
  const [mode, setMode] = useState("link");
  const [url, setUrl] = useState("");
  const [card, setCard] = useState<LinkCard | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  function add(value: Attachment) {
    onAdd(value);
    setUrl("");
    setCard(null);
    setError("");
  }

  async function resolve() {
    if (busy || disabled || !url.trim()) return;
    setBusy(true);
    setError("");
    try {
      const link = new URL(url.trim(), mode === "quote" ? window.location.origin : undefined);
      if (!["http:", "https:"].includes(link.protocol) || link.username || link.password)
        throw new Error("Use an HTTP or HTTPS URL without credentials.");

      if (mode === "link") {
        setCard(await api<LinkCard>("/links/preview", { method: "POST", body: JSON.stringify({ url: link.href }) }));
      } else if (mode === "quote") {
        add(await publicationReference(link));
      } else {
        const player = providers.map((provider) => ({ type: "embed" as const, provider, url: link.href }))
          .find((item) => embedSource(item) !== null);
        if (!player) throw new Error("Use a YouTube, Vimeo, Spotify, or SoundCloud resource link.");
        add(player);
      }
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusy(false);
    }
  }

  return <details className="my-3 rounded border border-neutral-200 p-3 text-sm">
    <summary className="cursor-pointer font-semibold">Add rich content</summary>
    <div className="mt-3 space-y-2">
      <label className="form-label block">Content type
        <select className="field mt-1" value={mode} disabled={busy || disabled} onChange={(event) => {
          setMode(event.target.value);
          setCard(null);
          setError("");
        }}>
          <option value="link">Link card</option>
          <option value="player">Embedded player</option>
          {allowQuote && <option value="quote">Quote a publication</option>}
        </select>
      </label>
      <label className="form-label block">URL<input className="field mt-1" value={url} maxLength={2048} disabled={busy || disabled}
        placeholder={mode === "quote" ? "Paste a post or article link" : "https://example.com"}
        onChange={(event) => { setUrl(event.target.value); setCard(null); }}
        onKeyDown={(event) => {
          if (event.key === "Enter") { event.preventDefault(); void resolve(); }
        }} /></label>
      {!card && <button type="button" className="button-secondary" disabled={busy || disabled || !url.trim()}
        onClick={() => void resolve()}>{busy ? "Loading…" : mode === "link" ? "Preview link" : "Add attachment"}</button>}
      {card && <>
        <label className="form-label block">Card title<input className="field mt-1" maxLength={300} value={card.title} disabled={disabled}
          onChange={(event) => setCard({ ...card, title: event.target.value })} /></label>
        <label className="form-label block">Description<textarea className="field mt-1" maxLength={1000} value={card.description}
          disabled={disabled} onChange={(event) => setCard({ ...card, description: event.target.value })} /></label>
        <button type="button" className="button-secondary" disabled={disabled || !card.title.trim()}
          onClick={() => add({ ...card, title: card.title.trim() })}>Add link card</button>
      </>}
      {error && <p className="notice-error" role="alert">{error}</p>}
    </div>
  </details>;
}
