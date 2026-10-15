import { useParams } from "react-router-dom";
import { useArticleEditor } from "./useArticleEditor";
import { EditorToolbar } from "./EditorToolbar";
import { EditorContent } from "@tiptap/react";
export function ArticleEditorPage() {
  const { articleId } = useParams();
  return <ArticleEditorForm key={articleId || "new"} />;
}
function ArticleEditorForm() {
  const { loading, loadError, title, setTitle, summary, setSummary, article, error, saving, setThumbnailFile, thumbnailPreview, publishAt, setPublishAt, imageInput, editor, uploadInlineImage, runAction } = useArticleEditor();
  if (loading)
    return <p role="status">Loading article…</p>;
  if (loadError)
    return <div className="notice-error">{loadError}</div>;
  const preview = thumbnailPreview || article?.thumbnail_url;
  return <div className="mx-auto max-w-4xl space-y-5">
    <div className="flex flex-wrap items-end justify-between gap-3">
      <div>
        <p className="eyebrow">Writing room</p>
        <p className="editorial-title text-sm font-semibold text-neutral-500">
          {article ? "Edit article" : "New article"}
        </p>
      </div>
      <span className="pill">
        {article?.status || "draft"}
      </span>
    </div>
    <div className="surface p-5 sm:p-9">
      <h1 className="editorial-title">
        <input aria-label="Article title" className="w-full border-0 bg-transparent p-0 text-4xl font-semibold leading-tight tracking-tight text-black outline-none placeholder:text-neutral-300 sm:text-5xl" maxLength={160} placeholder="Give your story a title" value={title} onChange={(event) => setTitle(event.target.value)} />
      </h1>
      <div className="mt-7 rounded border border-dashed border-neutral-300 p-3">
        {preview ? <img className="mb-3 h-48 w-full object-cover sm:h-64" src={preview} alt="Article thumbnail preview" /> : <div className="mb-3 flex h-24 w-full items-center justify-center bg-neutral-50 text-xs text-neutral-400">Wide cover image · optional</div>}
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-sm font-semibold text-black">Cover image</p>
            <p className="mt-1 text-xs text-neutral-500">JPEG, PNG, or WebP · up to 10 MB</p>
          </div>
          <label className="button-secondary cursor-pointer">
            {preview ? "Replace image" : "Choose image"}
            <input className="sr-only" type="file" accept="image/jpeg,image/png,image/webp" onChange={(event) => setThumbnailFile(event.target.files?.[0] || null)} disabled={saving} />
          </label>
        </div>
      </div>
      <label className="form-label mt-6 block">Summary<textarea className="field mt-2 min-h-20 resize-y" maxLength={320} placeholder="A short introduction for readers" value={summary} onChange={(event) => setSummary(event.target.value)} /></label>
      <div className="mt-8">
        <p className="form-label mb-2 block">Story</p>
        {saving && <p role="status" className="mb-2 text-sm text-neutral-500">Saving your article and images…</p>}
        <EditorToolbar editor={editor} onAddImage={() => {
          if (!saving)
            imageInput.current?.click();
        }} />
        <input ref={imageInput} disabled={saving} className="hidden" type="file" accept="image/jpeg,image/png,image/webp" onChange={(event) => {
          const file = event.target.files?.[0]; if (file)
            void uploadInlineImage(file); event.currentTarget.value = "";
        }} />
        <div className="rounded-b border border-t-0 border-neutral-200 bg-white px-4 py-4">
          <EditorContent editor={editor} />
        </div>
      </div>
    </div>
    <section className="surface p-5 sm:p-7">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-black">Publishing</p>
          <p className="mt-1 text-sm text-neutral-500">Save a draft, publish now, or schedule a time.</p>
        </div>
        <span className="badge">
          {article?.status || "draft"}
        </span>
      </div>
      {article?.scheduled_at && <p className="mt-4 border border-neutral-200 px-3 py-2 text-sm text-neutral-600">Scheduled for {new Date(article.scheduled_at).toLocaleString()}</p>}
      <div className="mt-5 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <label className="form-label">Publish after<input className="field mt-1.5 sm:w-64" type="datetime-local" value={publishAt} onChange={(event) => setPublishAt(event.target.value)} /></label>
        <div className="flex flex-wrap gap-2">
          <button className="button-secondary" disabled={saving} onClick={() => void runAction("draft")}>Draft</button>
          {article && <button className="button-secondary" disabled={saving} onClick={() => void runAction("delete")}>Delete</button>}
          <button className="button-secondary" disabled={saving} onClick={() => void runAction("schedule")}>Publish after…</button>
          <button className="button-primary" disabled={saving} onClick={() => void runAction("publish")}>
            {saving ? "Saving…" : "Publish now"}
          </button>
        </div>
      </div>
      {error && <div className="notice-error mt-4">
        {error}
      </div>}
    </section>
  </div>;
}
