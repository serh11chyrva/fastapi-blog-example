import { useApp } from "../../app/AuthProvider";
import { useNavigate, useParams } from "react-router-dom";
import { useEffect, useRef, useState } from "react";
import type { JSONContent } from "@tiptap/core";
import type { Article } from "../../shared/api/types";
import { useEditor } from "@tiptap/react";
import { createEditorExtensions } from "./editorExtensions";
import { fromEditorBody, toEditorBody } from "./contentNodes";
import { api, errorMessage } from "../../shared/api/client";
import { useImageUploader, validateImages } from "../../shared/uploads/uploadImages";
export function useArticleEditor() {
  const { articleId } = useParams();
  const { user } = useApp();
  const navigate = useNavigate();
  const [title, setTitle] = useState("");
  const [summary, setSummary] = useState("");
  const [body, setBody] = useState<JSONContent>({ type: "doc", content: [{ type: "paragraph" }] });
  const [article, setArticle] = useState<Article | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [saving, setSaving] = useState(false);
  const uploadImages = useImageUploader();
  const [pendingInlineImage, setPendingInlineImage] = useState<File | null>(null);
  const [thumbnailFile, setThumbnailFile] = useState<File | null>(null);
  const [thumbnailPreview, setThumbnailPreview] = useState("");
  const [publishAt, setPublishAt] = useState("");
  const imageInput = useRef<HTMLInputElement>(null);
  const editor = useEditor({
    extensions: createEditorExtensions(),
    content: toEditorBody(body),
    editable: true,
    onUpdate: ({ editor: current }) => setBody(fromEditorBody(current.getJSON())),
    editorProps: { attributes: { class: "tiptap-content tiptap-editable" } },
  });
  const [loading, setLoading] = useState(!!articleId);
  const [loadError, setLoadError] = useState("");
  useEffect(() => {
    if (!articleId)
      return;
    const controller = new AbortController();
    api<Article>(`/articles/${articleId}`, { signal: controller.signal })
      .then((value) => {
        if (controller.signal.aborted)
          return;
        if (value.owner_id !== user?.id) {
          setLoadError("This article is unavailable for editing.");
          return;
        }
        setArticle(value);
        setTitle(value.title);
        setSummary(value.summary);
        setBody(value.body);
        if (value.scheduled_at) {
          const local = new Date(value.scheduled_at);
          local.setMinutes(local.getMinutes() - local.getTimezoneOffset());
          setPublishAt(local.toISOString().slice(0, 16));
        }
      })
      .catch((reason: unknown) => {
        if (!controller.signal.aborted)
          setLoadError(errorMessage(reason));
      })
      .finally(() => {
        if (!controller.signal.aborted)
          setLoading(false);
      });
    return () => controller.abort();
  }, [articleId, user?.id]);
  useEffect(() => {
    if (!thumbnailFile) {
      setThumbnailPreview("");
      return;
    }
    const url = URL.createObjectURL(thumbnailFile);
    setThumbnailPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [thumbnailFile]);
  useEffect(() => {
    if (editor && JSON.stringify(fromEditorBody(editor.getJSON())) !== JSON.stringify(body))
      editor.commands.setContent(toEditorBody(body), { emitUpdate: false });
  }, [editor, body]);
  function validateContent() {
    if (!title.trim())
      throw new Error("Add a title before saving your article.");
    if (thumbnailFile) validateImages("/cover", [thumbnailFile]);
  }
  async function persist(): Promise<Article> {
    validateContent();
    const payload = { title, summary, body };
    let saved = article;
    if (!saved) {
      saved = await api<Article>("/articles", { method: "POST", body: JSON.stringify(payload) });
    } else if (title.trim() !== saved.title || summary.trim() !== saved.summary || JSON.stringify(body) !== JSON.stringify(saved.body)) {
      saved = await api<Article>(`/articles/${saved.id}`, { method: "PATCH", body: JSON.stringify(payload) });
    }
    setArticle(saved);
    if (thumbnailFile) {
      saved = await uploadImages<Article>(`/articles/${saved.id}/cover`, [thumbnailFile]);
      setThumbnailFile(null);
    }
    setArticle(saved);
    return saved;
  }
  async function uploadInlineImage(file: File) {
    if (saving)
      return;
    setSaving(true);
    setError("");
    try {
      validateImages("/images", [file]);
      setPendingInlineImage(file);
      const saved = article || await persist();
      const uploaded = await uploadImages<{
        url: string;
        alt_text: string;
      }>(`/articles/${saved.id}/images`, [file]);
      editor?.chain().focus().insertContent({ type: "image", attrs: { src: uploaded.url, alt: uploaded.alt_text } }).run();
      setPendingInlineImage(null);
    }
    catch (reason) {
      setError(errorMessage(reason));
    }
    finally {
      setSaving(false);
    }
  }
  async function removeCover() {
    if (saving) return;
    if (!article?.thumbnail_url) {
      setThumbnailFile(null);
      return;
    }
    setSaving(true);
    setError("");
    setNotice("");
    try {
      await api(`/articles/${article.id}/cover`, { method: "DELETE" });
      setThumbnailFile(null);
      setArticle({ ...article, thumbnail_url: null });
      setNotice("Cover removed.");
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setSaving(false);
    }
  }

  async function runAction(action: "save" | "draft" | "delete" | "publish" | "schedule") {
    if (saving) return;
    if (action === "delete" && (!article || !confirm("Delete this article? This removes it from public pages.")))
      return;
    if (action === "schedule" && !publishAt) {
      setError("Choose a date and time for publication.");
      return;
    }
    setSaving(true);
    setError("");
    setNotice("");
    let transitionFrom: Article | null = null;
    try {
      if (action === "delete" && article) {
        await api(`/articles/${article.id}`, { method: "DELETE" });
        navigate("/my-articles");
        return;
      }
      validateContent();
      let scheduledTime: string | undefined;
      if (action === "schedule") {
        const date = new Date(publishAt);
        if (!Number.isFinite(date.getTime()) || date.getTime() <= Date.now())
          throw new Error("Choose a future date and time for publication.");
        scheduledTime = date.toISOString();
      }
      const saved = await persist();
      if (action === "save") {
        setNotice("Changes saved.");
        if (!articleId) navigate(`/articles/${saved.id}/edit`, { replace: true });
        return;
      }
      if (action === "delete") return;

      transitionFrom = saved;
      const updated = action === "draft" && saved.status === "draft" ? saved
        : await api<Article>(`/articles/${saved.id}/${action}`, {
            method: "POST", ...(scheduledTime ? { body: JSON.stringify({ publish_at: scheduledTime }) } : {}),
          });
      setArticle(updated);
      setNotice(action === "draft" ? "Moved to draft." : action === "schedule" ? "Publication scheduled." : "Published.");
      if (!articleId) navigate(`/articles/${updated.id}/edit`, { replace: true });
    }
    catch (reason) {
      if (transitionFrom) {
        const current = await api<Article>(`/articles/${transitionFrom.id}`).catch(() => null);
        if (current) setArticle(current);
        setError(`Changes saved. ${current ? `Current status: ${current.status}.` : "Could not reload the current status."} ${errorMessage(reason)}`);
      } else {
        setError(errorMessage(reason));
      }
    }
    finally {
      setSaving(false);
    }
  }
  useEffect(() => { editor?.setEditable(!saving); }, [editor, saving]);
  return { loading, loadError, title, setTitle, summary, setSummary, article, error, saving, thumbnailFile, setThumbnailFile, thumbnailPreview, publishAt, setPublishAt, imageInput, editor, pendingInlineImage, uploadInlineImage, removeCover, notice, runAction };
}
