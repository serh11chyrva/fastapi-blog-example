import { useEffect, useMemo, useState } from "react";
import type { JSONContent } from "@tiptap/core";
import { Link } from "react-router-dom";
import type { Article, Profile, ProfileCard } from "../../shared/api/types";
import { useApp } from "../../app/AuthProvider";
import { api, errorMessage } from "../../shared/api/client";
import { Discussion } from "../comments/Discussion";
import { PublicationActions } from "../interactions/PublicationActions";
import { Attachments } from "../publications/Attachments";
import { PublicationAuthors } from "../publications/PublicationAuthors";
import { TipTapDocument } from "./TipTapDocument";

function readingSections(body: JSONContent) {
  const sections: { id: string; label: string; level: number }[] = [];
  function plainText(node: JSONContent): string {
    return node.text ?? (node.content?.map(plainText).join("") || "");
  }
  function visit(node: JSONContent): JSONContent {
    if (node.type === "heading") {
      const label = plainText(node).trim();
      if (label) {
        const id = `section-${sections.length + 1}`;
        sections.push({ id, label, level: Number(node.attrs?.level ?? 1) });
        return { ...node, attrs: { ...node.attrs, sectionId: id } };
      }
    }
    return node.content ? { ...node, content: node.content.map(visit) } : node;
  }

  return { document: visit(body), sections };
}

function ArticleAuthors({ authors }: { authors: ProfileCard[] }) {
  const { user } = useApp();
  const username = authors[0]?.username;
  const [profile, setProfile] = useState<Profile>();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const path = `/users/${encodeURIComponent(username ?? "")}`;
  useEffect(() => {
    const controller = new AbortController();
    setProfile(undefined);
    if (!username) return;
    api<Profile>(path, { signal: controller.signal })
      .then((value) => { if (!controller.signal.aborted) setProfile(value); })
      .catch(() => undefined);
    return () => controller.abort();
  }, [username, path, user?.id]);

  async function toggleFollow() {
    if (!profile || !user || busy) return;
    setBusy(true);
    setError("");
    try {
      await api(`${path}/follow`, { method: profile.is_following ? "DELETE" : "PUT" });
      setProfile(await api<Profile>(path));
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusy(false);
    }
  }

  return <aside className="mt-10 border-y border-neutral-200 py-5" aria-label="About the authors">
    <p className="eyebrow mb-3">Written by</p>
    <div className="flex flex-wrap items-start justify-between gap-4">
      <PublicationAuthors authors={authors} />
      {profile && user && profile.id !== user.id && <button className="button-secondary" disabled={busy}
        onClick={() => void toggleFollow()}>{profile.is_following ? "Following" : "Follow"}</button>}
    </div>
    {profile?.bio && <p className="mt-3 whitespace-pre-wrap text-sm leading-6 text-neutral-700">{profile.bio}</p>}
    {profile?.location && <p className="mt-1 text-sm text-neutral-500">{profile.location}</p>}
    {error && <p role="alert" className="notice-error mt-3">{error}</p>}
  </aside>;
}

export function ArticlePresentation({ article, owner }: { article: Article; owner: boolean }) {
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState("");
  const [comments, setComments] = useState(true);
  const { document, sections } = useMemo(() => readingSections(article.body), [article.body]);
  const dateFormat = new Intl.DateTimeFormat("en", { month: "long", day: "numeric", year: "numeric" });
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
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-neutral-500">{article.published_at ? <>
          <time dateTime={article.published_at}>{dateFormat.format(new Date(article.published_at))}</time>
          {Date.parse(article.updated_at) > Date.parse(article.published_at) && <> · Updated{" "}
            <time dateTime={article.updated_at}>{dateFormat.format(new Date(article.updated_at))}</time>
          </>}
        </> : article.status}</p>
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
    {!!sections.length && <nav className="my-8 rounded border border-neutral-200 p-4" aria-label="In this article">
      <p className="eyebrow mb-2">In this article</p>
      <ol className="space-y-1 text-sm">
        {sections.map((section) => <li key={section.id} className={section.level > 2 ? "pl-3" : ""}>
          <a className="underline underline-offset-2" href={`#${section.id}`}>{section.label}</a>
        </li>)}
      </ol>
    </nav>}
    <div className="article-body mt-10"><TipTapDocument body={document} /></div>
    <Attachments items={article.attachments.filter((item) => item.type !== "image" || !bodyImages.has(item.url))} />
    <ArticleAuthors authors={article.authors} />
    {error && <p className="notice-error mt-4" role="alert">{error}</p>
    {article.status === "published" && <>
      <PublicationActions key={article.id} kind="article" id={article.id} onComments={() => setComments((value) => !value)} />
      {comments && <Discussion key={article.id} kind="article" id={article.id} deepLink />}
    </>}
  </article>;
}
