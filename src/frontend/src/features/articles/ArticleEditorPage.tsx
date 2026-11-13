import { useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { EditorContent } from "@tiptap/react";
import { usePageTitle } from "../../app/usePageTitle";
import { Icon } from "../../shared/ui/Icon";
import { articleBlockDragType, EditorToolbar, moveArticleBlock } from "./EditorToolbar";
import { useArticleEditor } from "./useArticleEditor";
import { ArticleSectionNavigation } from "./ArticleSections";

export function ArticleEditorPage() {
  const { articleId } = useParams();
  return <ArticleEditorForm key={articleId || "new"} />;
}

function ArticleEditorForm() {
  const { loading, loadError, title, setTitle, article, error, saving, setThumbnailFile, thumbnailPreview,
    publishAt, setPublishAt, imageInput, chooseInlineImage, editor, inlinePreview, pendingInlineImage, uploadInlineImage, removeCover, notice, runAction } = useArticleEditor();
  const [dropTop, setDropTop] = useState<number | null>(null);
  const workspace = useRef<HTMLDivElement>(null);
  const publishDialog = useRef<HTMLDialogElement>(null);
  usePageTitle(loading ? "Loading editor" : loadError ? "Editor unavailable" : article ? `Edit ${article.title}` : "Write an article");
  if (loading) return <p className="list-status" role="status">Loading article…</p>;
  if (loadError) return <p className="notice-error" role="alert">{loadError}</p>;

  function dropGap(clientY: number) {
    if (!editor || !workspace.current) return null;
    const gaps: { index: number; y: number }[] = [];
    editor.state.doc.forEach((_node, from, index) => {
      const element = editor.view.nodeDOM(from);
      if (element instanceof HTMLElement) {
        const rect = element.getBoundingClientRect();
        gaps.push({ index, y: rect.top });
        if (index === editor.state.doc.childCount - 1) gaps.push({ index: index + 1, y: rect.bottom });
      }
    });
    return gaps.reduce<{ index: number; y: number } | null>((best, gap) =>
      !best || Math.abs(gap.y - clientY) < Math.abs(best.y - clientY) ? gap : best, null);
  }
  const preview = thumbnailPreview || article?.thumbnail_url;
  const status = article?.status ?? "draft";
  return <article className="writer">
    <ArticleSectionNavigation editor={editor} />
    <div className="writer-actions">
      <span className="writer-state">{saving ? "Saving…" : article?.archived_at ? "archived" : status}</span>
      <button type="button" className="button-secondary" disabled={saving} onClick={() => void runAction("save")}>Save</button>
      <button type="button" className="button-primary" disabled={saving} onClick={() => publishDialog.current?.showModal()}>Publish</button>
    </div>
    <header className="writer-hero">
      {preview ? <figure className="article-cover writer-cover">
        <img src={preview} alt="Article cover" />
        <div className="cover-edit">
          <label className="cover-change">Change cover
            <input className="sr-only" type="file" accept="image/jpeg,image/png,image/webp" disabled={saving}
              onChange={(event) => { const file = event.target.files?.[0]; if (file) setThumbnailFile(file); event.target.value = ""; }} />
          </label>
          <button type="button" className="cover-change" aria-label="Remove cover" disabled={saving} onClick={() => void removeCover()}>
            <Icon name="close" width={16} height={16} />
          </button>
        </div>
      </figure> : <label className="add-cover"><Icon name="plus" width={17} height={17} /> Add a cover
        <input className="sr-only" type="file" accept="image/jpeg,image/png,image/webp" disabled={saving}
          onChange={(event) => { const file = event.target.files?.[0]; if (file) setThumbnailFile(file); event.target.value = ""; }} />
      </label>}
      <textarea aria-label="Article title" className="writer-title" disabled={saving} maxLength={160}
        placeholder="Untitled" rows={1} value={title} onChange={(event) => setTitle(event.target.value)}
        onKeyDown={(event) => { if (event.key === "Enter") { event.preventDefault(); editor?.commands.focus("start"); } }} />
    </header>
    <div className="writer-body" ref={workspace}
      onDragOverCapture={(event) => {
        if (event.dataTransfer.types.includes(articleBlockDragType)) {
          event.preventDefault();
          event.dataTransfer.dropEffect = "move";
          const gap = dropGap(event.clientY);
          if (gap) setDropTop(gap.y - (workspace.current?.getBoundingClientRect().top ?? 0));
        }
      }}
      onDragEnd={() => setDropTop(null)}
      onDragLeave={(event) => { if (!event.currentTarget.contains(event.relatedTarget as Node | null)) setDropTop(null); }}
      onDropCapture={(event) => {
        const raw = event.dataTransfer.getData(articleBlockDragType);
        if (!raw || !editor || saving) return;
        event.preventDefault();
        event.stopPropagation();
        const gap = dropGap(event.clientY);
        const source = Number(raw);
        if (gap && Number.isInteger(source)) moveArticleBlock(editor, source, gap.index > source ? gap.index - 1 : gap.index);
        setDropTop(null);
      }}>
      <EditorToolbar editor={editor} workspace={workspace} disabled={saving} onAddImage={chooseInlineImage} />
      {dropTop !== null && <div className="editor-drop-indicator" style={{ top: dropTop }} aria-hidden="true" />}
      <EditorContent editor={editor} />
      <input ref={imageInput} disabled={saving} className="hidden" type="file" accept="image/jpeg,image/png,image/webp,image/gif" onChange={(event) => {
        const file = event.target.files?.[0];
        if (file) void uploadInlineImage(file);
        event.currentTarget.value = "";
      }} />
      <p className="text-xs text-slate-500">Inline images: JPEG, PNG, or WebP up to 5 MiB; GIF up to 8 MiB. Covers do not support GIF.</p>
      {inlinePreview && <figure className="pending-article-image"><img src={inlinePreview} alt="Image awaiting insertion" /><figcaption>{saving ? "Uploading image…" : "Upload pending — retry to insert this image."}</figcaption></figure>}
      {pendingInlineImage && <button type="button" className="button-secondary" disabled={saving}
        onClick={() => void uploadInlineImage(pendingInlineImage)}>Retry image upload</button>}
    </div>
    {notice && <p className="writer-feedback" role="status">{notice}</p>}
    {error && <p className="notice-error" role="alert">{error}</p>}
    <dialog className="design-dialog publish-dialog" aria-labelledby="publish-title" ref={publishDialog}>
      <div className="dialog-heading">
        <h2 id="publish-title">Publishing</h2>
        <button type="button" className="icon-button" aria-label="Close publishing" onClick={() => publishDialog.current?.close()}>
          <Icon name="close" />
        </button>
      </div>
      <div className="dialog-body">
        <p className="writer-state">Status · {article?.archived_at ? "archived" : status}</p>
        {article?.archived_at && <p>Unarchive this article from its page before changing publication settings.</p>}
        {article?.scheduled_at && <p className="writer-state">Scheduled for {new Date(article.scheduled_at).toLocaleString()}</p>}
        <label className="form-label">Schedule for<input className="field" type="datetime-local" disabled={saving}
          value={publishAt} onChange={(event) => setPublishAt(event.target.value)} /></label>
        <div className="publish-actions">
          <button type="button" className="button-primary" disabled={saving || !!article?.archived_at} onClick={() => void runAction("publish")}>Publish now</button>
          <button type="button" className="button-secondary" disabled={saving || !!article?.archived_at || !publishAt} onClick={() => void runAction("schedule")}>Schedule</button>
          {article && status !== "draft" && <button type="button" className="button-secondary" disabled={saving || !!article.archived_at}
            onClick={() => void runAction("draft")}>Move to draft</button>}
          {article && <button type="button" className="button-quiet" disabled={saving} onClick={() => void runAction("delete")}>Delete article</button>}
        </div>
        {article && <Link className="text-link" to={status === "published" ? article.share_url ?? `/articles/${article.id}` : `/articles/${article.id}`}>View article</Link>}
        {notice && <p className="writer-feedback" role="status">{notice}</p>}
        {error && <p className="notice-error" role="alert">{error}</p>}
      </div>
    </dialog>
  </article>;
}
