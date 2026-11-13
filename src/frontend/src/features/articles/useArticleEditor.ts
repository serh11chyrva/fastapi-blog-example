import { useApp } from "../../app/AuthProvider";
import { useNavigate, useParams } from "react-router-dom";
import { useEffect, useRef, useState } from "react";
import type { JSONContent } from "@tiptap/core";
import type { Article, HeroLayout } from "../../shared/api/types";
import { useEditor } from "@tiptap/react";
import { createEditorExtensions } from "./editorExtensions";
import { replaceArticleImageEvent } from "./ArticleImage";
import type { InsertionRange } from "./EditorToolbar";
import type { Transaction } from "@tiptap/pm/state";
import { fromEditorBody, toEditorBody } from "./contentNodes";
import { api, errorMessage } from "../../shared/api/client";
import { useImageUploader, validateImages } from "../../shared/uploads/uploadImages";
export function useArticleEditor() {
  const { articleId } = useParams();
  const { user } = useApp();
  const navigate = useNavigate();
  const [title, setTitle] = useState("");
  const [heroLayout, setHeroLayout] = useState<HeroLayout>("cover_title");
  const [commentsEnabled, setCommentsEnabled] = useState(true);
  const [searchEnabled, setSearchEnabled] = useState(true);
  const [loadedBody, setLoadedBody] = useState<JSONContent | null>(null);
  const [body, setBody] = useState<JSONContent>({ type: "doc", content: [{ type: "paragraph" }] });
  const [article, setArticle] = useState<Article | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [saving, setSaving] = useState(false);
  const uploadImages = useImageUploader();
  const [pendingInlineImage, setPendingInlineImage] = useState<File | null>(null);
  const [thumbnailFile, setThumbnailFile] = useState<File | null>(null);
  const [thumbnailPreview, setThumbnailPreview] = useState("");
  const [coverRemoved, setCoverRemoved] = useState(false);
  const [publishAt, setPublishAt] = useState("");
  const imageInput = useRef<HTMLInputElement>(null);
  const imageAttributes = useRef<{ alt: string; title: string | null } | null>(null);
  const operation = useRef(false);
  const [inlinePreview, setInlinePreview] = useState("");
  const imagePosition = useRef<InsertionRange | null>(null);
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
        setHeroLayout(value.hero_layout ?? "cover_title");
        setCommentsEnabled(value.comments_enabled ?? true);
        setSearchEnabled(value.search_enabled ?? true);
        setBody(value.body);
        setLoadedBody(value.body);
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
    if (editor && loadedBody) editor.commands.setContent(toEditorBody(loadedBody), { emitUpdate: false });
  }, [editor, loadedBody]);
  useEffect(() => {
    if (!pendingInlineImage) { setInlinePreview(""); return; }
    const url = URL.createObjectURL(pendingInlineImage);
    setInlinePreview(url);
    return () => URL.revokeObjectURL(url);
  }, [pendingInlineImage]);
  useEffect(() => {
    if (!editor) return;
    function mapImage({ transaction }: { transaction: Transaction }) {
      if (imagePosition.current) imagePosition.current = {
        from: transaction.mapping.map(imagePosition.current.from, -1),
        to: transaction.mapping.map(imagePosition.current.to, 1),
      };
    }
    function replace(event: Event) {
      const detail = (event as CustomEvent<InsertionRange & { alt: string; title: string | null }>).detail;
      imagePosition.current = { from: detail.from, to: detail.to };
      imageAttributes.current = { alt: detail.alt, title: detail.title };
      imageInput.current?.click();
    }
    editor.view.dom.addEventListener(replaceArticleImageEvent, replace);
    editor.on("transaction", mapImage);
    return () => { editor.off("transaction", mapImage); editor.view.dom.removeEventListener(replaceArticleImageEvent, replace); };
  }, [editor]);
  function chooseInlineImage(range: InsertionRange) {
    imagePosition.current = range;
    imageAttributes.current = null;
    imageInput.current?.click();
  }
  function validateContent() {
    if (!title.trim())
      throw new Error("Add a title before saving your article.");
    if (thumbnailFile) validateImages("article-covers", [thumbnailFile]);
  }
  function chooseCover(file: File) {
    try {
      validateImages("article-covers", [file]);
      setThumbnailFile(file);
      setCoverRemoved(false);
      setError("");
      setNotice("");
    } catch (reason) { setError(errorMessage(reason)); }
  }
  async function persist(): Promise<Article> {
    validateContent();
    const currentBody = editor ? fromEditorBody(editor.getJSON()) : body;
    const payload = { title, body: currentBody, hero_layout: heroLayout,
      comments_enabled: commentsEnabled, search_enabled: searchEnabled };
    let saved = article;
    if (!saved) {
      saved = await api<Article>("/articles", { method: "POST", body: JSON.stringify(payload) });
    } else if (title.trim() !== saved.title || heroLayout !== (saved.hero_layout ?? "cover_title")
      || commentsEnabled !== (saved.comments_enabled ?? true)
      || searchEnabled !== (saved.search_enabled ?? true)
      || JSON.stringify(currentBody) !== JSON.stringify(saved.body)) {
      saved = await api<Article>(`/articles/${saved.id}`, { method: "PATCH", body: JSON.stringify(payload) });
    }
    setArticle(saved);
    if (thumbnailFile) {
      saved = await uploadImages<Article>(`/articles/${saved.id}/cover`, [thumbnailFile]);
      saved = await api<Article>(`/articles/${saved.id}`);
      setThumbnailFile(null);
    } else if (coverRemoved && saved.thumbnail_url) {
      await api(`/articles/${saved.id}/cover`, { method: "DELETE" });
      saved = await api<Article>(`/articles/${saved.id}`);
    }
    setCoverRemoved(false);
    setArticle(saved);
    return saved;
  }
  async function uploadInlineImage(file: File) {
    if (operation.current) return;
    operation.current = true;
    setSaving(true);
    setError("");
    try {
      validateImages("article-images", [file]);
      setPendingInlineImage(file);
      let saved = article;
      if (!saved) {
        saved = await api<Article>("/articles", {
          method: "POST", body: JSON.stringify({ title: title.trim() || "Untitled",
            body: editor ? fromEditorBody(editor.getJSON()) : body, hero_layout: heroLayout,
            comments_enabled: commentsEnabled, search_enabled: searchEnabled }),
        });
        setArticle(saved);
      }
      const uploaded = await uploadImages<{
        url: string;
        alt_text: string;
      }>(`/articles/${saved.id}/images`, [file]);
      if (editor) {
        const range = imagePosition.current ?? { from: editor.state.selection.from, to: editor.state.selection.to };
        imagePosition.current = null;
        const replacing = range.to > range.from && editor.state.doc.nodeAt(range.from)?.type.name === "image";
        const image = { type: "image", attrs: { src: uploaded.url, alt: imageAttributes.current?.alt || uploaded.alt_text,
          title: imageAttributes.current?.title ?? null } };
        editor.chain().focus().insertContentAt(range, replacing ? image : [image, { type: "paragraph" }]).run();
        imageAttributes.current = null;
        editor.commands.focus();
      }
      setPendingInlineImage(null);
    }
    catch (reason) {
      setError(errorMessage(reason));
    }
    finally {
      operation.current = false;
      setSaving(false);
    }
  }
  function removeCover() {
    if (operation.current) return;
    setThumbnailFile(null);
    setCoverRemoved(true);
    setError("");
    setNotice("Cover will be removed when you save.");
  }

  async function runAction(action: "save" | "draft" | "delete" | "publish" | "schedule") {
    if (operation.current) return;
    if (action === "delete" && (!article || !confirm("Delete this article? This removes it from public pages.")))
      return;
    if (action === "schedule" && !publishAt) {
      setError("Choose a date and time for publication.");
      return;
    }
    operation.current = true;
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
      operation.current = false;
      setSaving(false);
    }
  }
  useEffect(() => { editor?.setEditable(!saving); }, [editor, saving]);
  const coverPreview = thumbnailPreview || (coverRemoved ? null : article?.thumbnail_url);
  return { loading, loadError, title, setTitle, heroLayout, setHeroLayout, commentsEnabled, setCommentsEnabled, article, error, saving,
    searchEnabled, setSearchEnabled,
    chooseCover, coverPreview, publishAt, setPublishAt, imageInput, chooseInlineImage, editor,
    inlinePreview, pendingInlineImage, uploadInlineImage, removeCover, notice, runAction };
}
