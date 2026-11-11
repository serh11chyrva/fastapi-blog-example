import { useEffect, useRef, useState } from "react";
import { api, errorMessage } from "../../shared/api/client";
import type { Article, Attachment, MicroPost } from "../../shared/api/types";

async function publicationReference(url: URL, signal: AbortSignal): Promise<Attachment> {
  if (url.origin !== window.location.origin) throw new Error("Use a link to a publication on this site.");
  const parts = url.pathname.split("/").filter(Boolean);
  if (parts.length !== 2) throw new Error("Use the link to a post or article.");
  const [section, id] = parts;
  if ((section === "posts" || section === "articles") && /^[0-9a-f]{24}$/i.test(id)) {
    const result = await api<MicroPost | Article>(`/${section}/${id}`, { signal });
    if (result.kind === "article" && result.status !== "published") throw new Error("This article is unavailable.");
    return result.kind === "article" ? { type: "article", article_id: result.id } : { type: "post", post_id: result.id };
  }
  const username = decodeURIComponent(section).replace(/^@/, "");
  const result = await api<MicroPost | Article>(`/publications/${encodeURIComponent(username)}/${id}`, { signal });
  return result.kind === "article" ? { type: "article", article_id: result.id } : { type: "post", post_id: result.id };
}

export function AttachmentComposer({ onAdd, disabled = false, initialMode }: {
  onAdd: (attachment: Attachment) => void;
  disabled?: boolean;
  initialMode?: "link" | "player" | "quote";
}) {
  const [mode, setMode] = useState<string>(initialMode ?? "link");
  const [url, setUrl] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const request = useRef<AbortController | null>(null);
  useEffect(() => () => request.current?.abort(), []);

  function add(value: Attachment) {
    onAdd(value);
    setUrl("");
    setError("");
  }

  async function resolve() {
    if (request.current || disabled || !url.trim()) return;
    const controller = new AbortController();
    request.current = controller;
    setBusy(true);
    setError("");
    try {
      const link = new URL(url.trim(), mode === "quote" ? window.location.origin : undefined);
      if (!["http:", "https:"].includes(link.protocol) || link.username || link.password)
        throw new Error("Use an HTTP or HTTPS URL without credentials.");

      if (mode === "quote") {
        const reference = await publicationReference(link, controller.signal);
        if (!controller.signal.aborted) add(reference);
      } else {
        const resolved = await api<{ attachment: Attachment }>("/links/resolve", {
          method: "POST", body: JSON.stringify({ url: link.href }), signal: controller.signal,
        });
        if (!controller.signal.aborted) add(resolved.attachment);
      }
    } catch (reason) {
      if (!controller.signal.aborted) setError(errorMessage(reason));
    } finally {
      if (!controller.signal.aborted) setBusy(false);
      request.current = null;
    }
  }

  const fields = <div className="attachment-fields">
      {!initialMode && <label className="form-label block">Content type
        <select className="field mt-1" value={mode} disabled={busy || disabled} onChange={(event) => {
          setMode(event.target.value);
          setError("");
        }}>
          <option value="link">Link or player (automatic)</option>
          <option value="player">Embedded player</option>
          <option value="quote">Quote a publication</option>
        </select>
      </label>}
      <label className="form-label block">URL<input className="field mt-1" value={url} maxLength={2048} disabled={busy || disabled}
        placeholder={mode === "quote" ? "Paste a post or article link" : "https://example.com"}
        onChange={(event) => setUrl(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === "Enter") { event.preventDefault(); void resolve(); }
        }} /></label>
      <button type="button" className="button-secondary" disabled={busy || disabled || !url.trim()}
        onClick={() => void resolve()}>{busy ? "Loading..." : "Add attachment"}</button>
      {error && <p className="notice-error" role="alert">{error}</p>}
    </div>;
  return initialMode ? fields : <details className="attachment-composer">
    <summary>Add rich content</summary>{fields}
  </details>;
}
