import { useState } from "react";
import type { MicroPost } from "../../shared/api/types";
import type { FormEvent } from "react";
import { api, errorMessage } from "../../shared/api/client";
import { uploadImages } from "../../shared/uploads/uploadImages";
export function PostComposer({ onPosted }: {
  onPosted: () => void;
}) {
  const [text, setText] = useState("");
  const [images, setImages] = useState<File[]>([]);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [pendingPost, setPendingPost] = useState<MicroPost | null>(null);
  async function submit(event: FormEvent) {
    event.preventDefault(); setSaving(true); setError(""); try {
      const post = await api<MicroPost>(pendingPost ? `/posts/${pendingPost.id}` : "/posts", { method: pendingPost ? "PATCH" : "POST", body: JSON.stringify({ text }) });
      setPendingPost(post);
      if (images.length)
        await uploadImages<MicroPost>(`/posts/${post.id}/images`, images);
      setPendingPost(null);
      setText("");
      setImages([]);
      onPosted();
    }
      catch (reason) {
        setError(errorMessage(reason));
        onPosted();
      }
      finally {
      setSaving(false);
    }
  }
  function chooseFiles(files: FileList | null) {
    if (!files)
      return; const selected = Array.from(files); if (selected.length > 5) {
        setError("Choose up to five images.");
        return;
      } setImages(selected);
  }
  return <form onSubmit={submit} className="surface p-4 sm:p-5">
    <div className="flex gap-3">
      <div className="grid h-10 w-10 shrink-0 place-items-center bg-neutral-100 font-serif text-lg font-semibold text-black">✎</div>
      <div className="min-w-0 flex-1">
        <textarea className="min-h-20 w-full resize-y border-0 bg-transparent p-1 text-[15px] leading-6 outline-none placeholder:text-slate-400" placeholder="What’s on your mind?" maxLength={280} value={text} onChange={(event) => setText(event.target.value)} />
        {images.length > 0 && <p className="mb-3 text-xs text-neutral-500">
          {images.map((file) => file.name).join(" · ")}
        </p>}
        <div className="flex flex-wrap items-center justify-between gap-2 border-t border-slate-100 pt-3">
          <div className="flex items-center gap-3">
            <span className="text-xs text-slate-400">{text.length} / 280</span>
            <label className="cursor-pointer text-xs font-semibold text-neutral-600 hover:text-black">Add images<input className="sr-only" type="file" disabled={saving} accept="image/jpeg,image/png,image/webp" multiple onChange={(event) => chooseFiles(event.target.files)} /></label>
            <span className="text-xs text-neutral-400">Up to 5</span>
          </div>
          <button className="button-primary" disabled={saving || !text.trim()}>
            {saving ? "Posting…" : "Share note"}
          </button>
        </div>
        {error && <p className="mt-2 text-sm text-slate-700">
          {error}
        </p>}
      </div>
    </div>
  </form>;
}
