import { useState } from "react";
import type { JSONContent } from "@tiptap/core";
import { Link } from "react-router-dom";
import type { Article } from "../../shared/api/types";
import { errorMessage } from "../../shared/api/client";
import { Discussion } from "../comments/Discussion";
import { PublicationActions } from "../interactions/PublicationActions";
import { Attachments } from "../publications/Attachments";
import { PublicationAuthors } from "../publications/PublicationAuthors";
import { TipTapDocument } from "./TipTapDocument";

export function ArticlePresentation({ article, owner }: { article: Article; owner: boolean }) {
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState("");
  const [comments, setComments] = useState(true);
  const bodyImages = new Set<string>();
  const pending: JSONContent[] = [article.body];
  while (pending.length) {
    const node = pending.pop()!;
    if (node.type === "image" && typeof node.attrs?.src === "string") bodyImages.add(node.attrs.src);
    if (node.type === "attachment" && node.attrs?.type === "image") bodyImages.add(node.attrs.url);
    pending.push(...(node.content ?? []));
  }
  async function share() {
    try {
      await navigator.clipboard.writeText(new URL(article.share_url || `/articles/${article.id}`, window.location.origin).toString());
      setCopied(true);
    } catch (reason) { setError(errorMessage(reason)); }
  }
  return <article className="mx-auto max-w-[760px] pb-20">
    <div className="mb-8 space-y-4 border-b border-neutral-200 pb-5">
      <PublicationAuthors authors={article.authors} />
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-neutral-500">{article.published_at
          ? new Date(article.published_at).toLocaleDateString("en", { month: "long", day: "numeric", year: "numeric" })
          : article.status}</p>
        <div className="flex gap-2">
          {owner && <Link to={`/articles/${article.id}/edit`} className="button-secondary">Edit</Link>}
          {article.status === "published" && <button className="button-secondary" onClick={() => void share()}>
            {copied ? "Link copied" : "Share"}
          </button>}
        </div>
      </div>
    </div>
    <h1 className="editorial-title break-words text-4xl font-semibold leading-tight text-black sm:text-6xl">{article.title}</h1>
    {article.thumbnail_url && <img className="mt-8 max-h-[34rem] w-full object-cover" src={article.thumbnail_url} alt={`Cover for ${article.title}`} />}
    {article.summary && <p className="editorial-title mt-8 text-xl leading-8 text-neutral-600">{article.summary}</p>}
    {article.status !== "published" && <p className="mt-5 text-sm text-neutral-500">
      {article.status === "scheduled" ? `Scheduled · ${article.scheduled_at ? new Date(article.scheduled_at).toLocaleString() : ""}` : "Draft · only visible to you"}
    </p>}
    <div className="article-body mt-10"><TipTapDocument body={article.body} /></div>
    <Attachments items={article.attachments.filter((item) => item.type !== "image" || !bodyImages.has(item.url))} />
    {error && <p className="notice-error mt-4" role="alert">{error}</p>}
    {article.status === "published" && <>
      <PublicationActions key={article.id} kind="article" id={article.id} onComments={() => setComments((value) => !value)} />
      {comments && <Discussion key={article.id} kind="article" id={article.id} />}
    </>}
  </article>;
}
