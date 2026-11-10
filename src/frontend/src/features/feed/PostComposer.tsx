import { useState } from "react";
import { Icon } from "../../shared/ui/Icon";
import { AttachmentComposer } from "../publications/AttachmentComposer";
import { Attachments } from "../publications/Attachments";
import type { Attachment, MicroPost } from "../../shared/api/types";
import type { FormEvent } from "react";
import { api, errorMessage } from "../../shared/api/client";
import { useImageUploader, validateImages } from "../../shared/uploads/uploadImages";
export function PostComposer({ onPosted }: {
  onPosted: () => void;
}) {
  const [text, setText] = useState("");
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [images, setImages] = useState<File[]>([]);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const uploadImages = useImageUploader();
  const [pendingPost, setPendingPost] = useState<MicroPost | null>(null);
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (saving || !text.trim()) return;
    setSaving(true);
    setError("");
    let published = pendingPost;
    try {
      if (images.length) validateImages("/images", images);
      const post = await api<MicroPost>(pendingPost ? `/posts/${pendingPost.id}` : "/posts", { method: pendingPost ? "PATCH" : "POST", body: JSON.stringify({ text, attachments }) });
      published = post;
      setPendingPost(post);
      if (images.length)
        await uploadImages<MicroPost>(`/posts/${post.id}/images`, images);
      setPendingPost(null);
      setText("");
      setImages([]);
      setAttachments([]);
      onPosted();
    }
    catch (reason) {
      setError(published
        ? `Your note is already public. ${errorMessage(reason)} Retry will update this note.`
        : errorMessage(reason));
      if (published) onPosted();
    }
    finally {
      setSaving(false);
    }
  }
  function chooseFiles(files: FileList | null) {
    if (!files?.length) return;
    const selected = Array.from(files);
    setImages(selected);
    try {
      validateImages("/images", selected);
      setError("");
    } catch (reason) {
      setError(errorMessage(reason));
    }
  }
  return <form onSubmit={submit} className="post-composer">
    <div className="flex gap-3">
      <div className="min-w-0 flex-1">
        <textarea className="min-h-20 w-full resize-y border-0 bg-transparent p-1 text-[15px] leading-6 outline-none placeholder:text-slate-400" placeholder="What’s on your mind?" aria-label="Post text" disabled={saving} maxLength={280} value={text} onChange={(event) => setText(event.target.value)} />
        <AttachmentComposer disabled={saving || attachments.length >= 30}
          onAdd={(item) => setAttachments((items) => [...items, item])} />
        {attachments.map((item, index) => <div key={index} className="mb-2">
          <Attachments items={[item]} />
          <button type="button" className="text-xs underline" disabled={saving}
            onClick={() => setAttachments((items) => items.filter((_, position) => position !== index))}>
            Remove attachment
          </button>
        </div>)}
        {images.length > 0 && <p className="mb-3 text-xs text-neutral-500">
          {images.map((file) => file.name).join(" · ")}{" "}
          <button type="button" className="underline" disabled={saving}
            onClick={() => { setImages([]); setError(""); }}>Remove images</button>
        </p>}
        <div className="flex flex-wrap items-center justify-between gap-2 border-t border-slate-100 pt-3">
          <div className="flex items-center gap-3">
            <span className="text-xs text-slate-400">{text.length} / 280</span>
            <label className="cursor-pointer text-xs font-semibold text-neutral-600 hover:text-black"><Icon name="image" /> Add images<input className="sr-only" type="file" disabled={saving} accept="image/jpeg,image/png,image/webp" multiple onChange={(event) => { chooseFiles(event.target.files); event.currentTarget.value = ""; }} /></label>
            <span className="text-xs text-neutral-400">Up to 5</span>
          </div>
          <button className="button-primary" disabled={saving || !text.trim()}>
            {saving ? "Posting…" : "Post"}
          </button>
        </div>
        {error && <p className="mt-2 text-sm text-slate-700">
          {error}
        </p>}
      </div>
    </div>
  </form>;
}
