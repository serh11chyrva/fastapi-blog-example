import type { Article } from "../../shared/api/types";
import { useState } from "react";
import { Link } from "react-router-dom";
import { Avatar } from "../../shared/ui/Avatar";
import { TipTapDocument } from "./TipTapDocument";
export function ArticlePresentation({ article, owner }: {
  article: Article;
  owner: boolean;
}) {
  const [copied, setCopied] = useState(false);
  async function share() {
    if (!article.share_url)
      return;
    await navigator.clipboard.writeText(new URL(article.share_url, window.location.origin).toString());
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1800);
  }
  return <article className="mx-auto max-w-[760px] pb-20">
    <div className="mb-8 flex items-center justify-between border-b border-neutral-200 pb-5">
      <Link to={`/@${article.author_username}`} className="flex items-center gap-3">
        <Avatar src={article.author_avatar_url} name={article.author_display_name} />
        <div>
          <p className="font-semibold text-black">
            {article.author_display_name}
          </p>
          <p className="text-sm text-neutral-500">@{article.author_username} · {article.published_at ? new Date(article.published_at).toLocaleDateString("en", { month: "long", day: "numeric", year: "numeric" }) : article.status}</p>
        </div>
      </Link>
      <div className="flex gap-2">
        {owner && <Link to={`/articles/${article.id}/edit`} className="button-secondary">Edit</Link>}
        {article.status === "published" && <button className="button-secondary" onClick={() => void share()}>
          {copied ? "Link copied" : "Share"}
        </button>}
      </div>
    </div>
    <h1 className="editorial-title text-4xl font-semibold leading-[1.08] tracking-tight text-black sm:text-6xl">
      {article.title}
    </h1>
    {article.thumbnail_url ? <img className="mt-8 max-h-[34rem] w-full object-cover" src={article.thumbnail_url} alt={`Thumbnail for ${article.title}`} /> : <div className="mt-8 h-28 w-full bg-neutral-50" aria-label="No article cover image" />}
    {article.summary && <p className="editorial-title mt-8 text-xl leading-8 text-neutral-600 sm:text-2xl sm:leading-9">
      {article.summary}
    </p>}
    {article.status !== "published" && <div className="mt-5 inline-flex border border-neutral-300 px-3 py-1 text-xs font-semibold text-neutral-600">
      {article.status === "scheduled" ? `Scheduled · ${article.scheduled_at ? new Date(article.scheduled_at).toLocaleString() : ""}` : "Draft · only visible to you"}
    </div>}
    <div className="article-body mt-10">
      <TipTapDocument body={article.body} />
    </div>
  </article>;
}
