import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import type { Attachment, DiscussionComment, MicroPost } from "../../shared/api/types";
import { api, errorMessage } from "../../shared/api/client";
import { useImageUploader, validateImages } from "../../shared/uploads/uploadImages";
import { Icon } from "../../shared/ui/Icon";
import { AttachmentComposer } from "./AttachmentComposer";
import { Attachments } from "./Attachments";

type Image = Extract<Attachment, { type: "image" }>;

export function PublicationComposer({ post, replyPath, parentId, onSaved, onCancel, label = "Post" }: {
  post?: MicroPost; replyPath?: string; parentId?: string;
  onSaved: (saved: MicroPost | DiscussionComment) => void; onCancel?: () => void; label?: string;
}) {
  const [text, setText] = useState(post?.text ?? "");
  const [attachment, setAttachment] = useState<Attachment | null>(post?.attachments.find((item) => item.type !== "image") ?? null);
  const [retained, setRetained] = useState<Image[]>(post?.attachments.filter((item): item is Image => item.type === "image") ?? []);
  const [files, setFiles] = useState<File[]>([]);
  const [previews, setPreviews] = useState<string[]>([]);
  const [mode, setMode] = useState<"link" | "quote" | null>(null);
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState("");
  const [error, setError] = useState("");
  const lock = useRef(false);
  const draftKey = useRef(crypto.randomUUID());
  const draft = useRef<MicroPost | null>(null);
  const uploadedFiles = useRef<File[]>([]);
  const input = useRef<HTMLInputElement>(null);
  const upload = useImageUploader();
  const hasAttachment = !!attachment || files.length > 0 || retained.length > 0;

  useEffect(() => {
    const urls = files.map((file) => URL.createObjectURL(file));
    setPreviews(urls);
    return () => urls.forEach((url) => URL.revokeObjectURL(url));
  }, [files]);

  function clearAttachment() {
    setAttachment(null); setFiles([]); setRetained([]); setMode(null); setError("");
  }

  function chooseFiles(selected: FileList | null) {
    if (!selected?.length) return;
    const next = Array.from(selected);
    try {
      validateImages("/images", next);
      clearAttachment(); setFiles(next);
    } catch (reason) { setError(errorMessage(reason)); }
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (lock.current || (!text.trim() && !hasAttachment) || mode) return;
    lock.current = true; setBusy(true); setError("");
    try {
      if (!post || files.length) {
        setProgress("Preparing…");
        draft.current = await api<MicroPost>("/posts/drafts", {
          method: "POST", body: JSON.stringify({ key: draftKey.current }),
        });
        if (files.length && draft.current.pending && (files.length !== uploadedFiles.current.length
          || files.some((file, index) => file !== uploadedFiles.current[index]))) {
          setProgress("Uploading images…");
          draft.current = await upload<MicroPost>(`/posts/${draft.current.id}/images`, files);
          uploadedFiles.current = [...files];
        }
      }
      setProgress(post ? "Saving…" : "Publishing…");
      const attachments = attachment ? [attachment] : files.length ? [] : retained;
      const payload = {
        text, attachments,
        ...(post ? { expected_updated_at: post.updated_at } : {}),
        ...(post && files.length ? { image_draft_id: draft.current!.id }
          : { retain_image_urls: files.length ? draft.current!.attachments.filter((item) => item.type === "image").map((item) => item.url) : retained.map((item) => item.url) }),
        ...(replyPath ? { image_draft_id: draft.current!.id, ...(parentId ? { parent_id: parentId } : {}) } : {}),
      };
      const saved = !post && !replyPath && draft.current && !draft.current.pending ? draft.current
        : await api<MicroPost | DiscussionComment>(replyPath ?? `/posts/${post?.id ?? draft.current!.id}`, {
        method: replyPath ? "POST" : "PATCH", body: JSON.stringify(payload),
      });
      setText(""); clearAttachment(); draft.current = null; uploadedFiles.current = []; draftKey.current = crypto.randomUUID();
      onSaved(saved);
    } catch (reason) {
      setError(`${errorMessage(reason)} Your changes have been kept. Retry after resolving the error.`);
    } finally { lock.current = false; setBusy(false); setProgress(""); }
  }

  return <form className="post-composer publication-composer" onSubmit={submit}>
    <textarea className="field composer-text" aria-label={post ? "Edit post text" : "Publication text"}
      placeholder={replyPath ? "Write a reply or add an attachment…" : "What’s on your mind?"}
      maxLength={280} value={text} disabled={busy} onChange={(event) => setText(event.target.value)} />
    {(files.length > 0 || retained.length > 0) && <div className="composer-image-previews">
      {retained.map((item) => <figure key={item.url}>
        <img src={item.url} alt={item.alt || "Attached image"} />
        <button type="button" disabled={busy} aria-label="Remove image" onClick={() => setRetained((items) => items.filter((image) => image.url !== item.url))}><Icon name="close" /></button>
      </figure>)}
      {files.map((file, index) => <figure key={`${file.name}:${index}`}>
        <img src={previews[index]} alt={file.name} />
        <button type="button" disabled={busy} aria-label={`Remove ${file.name}`} onClick={() => setFiles((items) => items.filter((_, position) => position !== index))}><Icon name="close" /></button>
      </figure>)}
    </div>}
    {attachment && <Attachments items={[attachment]} />}
    {hasAttachment ? <div className="composer-attachment-actions">
      <button type="button" className="text-link" disabled={busy} onClick={clearAttachment}>Remove attachment</button>
      {(files.length > 0 || retained.length > 0) && <button type="button" className="text-link" disabled={busy} onClick={() => input.current?.click()}>Replace images</button>}
    </div> : <div className="composer-choices" aria-label="Choose one attachment type">
      <button type="button" className="button-quiet" disabled={busy} onClick={() => input.current?.click()}><Icon name="image" /> Images</button>
      <button type="button" className="button-quiet" disabled={busy} onClick={() => setMode("link")}><Icon name="link" /> Link or player</button>
      <button type="button" className="button-quiet" disabled={busy} onClick={() => setMode("quote")}><Icon name="book" /> Publication</button>
    </div>}
    <input ref={input} className="hidden" type="file" accept="image/jpeg,image/png,image/webp" multiple disabled={busy}
      onChange={(event) => { chooseFiles(event.target.files); event.currentTarget.value = ""; }} />
    {mode && <div className="composer-link-input">
      <AttachmentComposer key={mode} initialMode={mode} disabled={busy} onAdd={(item) => { setAttachment(item); setMode(null); }} />
      <button type="button" className="button-quiet" disabled={busy} onClick={() => setMode(null)}>Cancel attachment</button>
    </div>}
    <div className="comment-compose-actions">
      <span>{Array.from(text).length} / 280 · One attachment type · Up to 5 images</span>
      <div>{onCancel && <button type="button" className="button-quiet" disabled={busy} onClick={onCancel}>Cancel</button>}
        <button className="button-primary" disabled={busy || !!mode || (!text.trim() && !hasAttachment)}>{busy ? progress : label}</button>
      </div>
    </div>
    {busy && <p role="status" className="sr-only">{progress}</p>}
    {error && <p className="notice-error" role="alert">{error}</p>}
  </form>;
}
