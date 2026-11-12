import { useEffect, useMemo, useState } from "react";
import type { JSONContent } from "@tiptap/core";
import { Link, useLocation } from "react-router-dom";
import { useApp } from "../../app/AuthProvider";
import { Footer } from "../../app/layouts/Navigation";
import { api, errorMessage } from "../../shared/api/client";
import type { Article, Profile, ProfileCard } from "../../shared/api/types";
import { Avatar } from "../../shared/ui/Avatar";
import { Icon } from "../../shared/ui/Icon";
import { exactDateTime, publicationDate } from "../../shared/ui/dates";
import { Discussion } from "../comments/Discussion";
import { PublicationActions } from "../interactions/PublicationActions";
import { PublicationMenu } from "../publications/PublicationMenu";
import { PublicationStatus } from "../publications/PublicationStatus";
import { Attachments } from "../publications/Attachments";
import { TipTapDocument } from "./TipTapDocument";

function readingSections(body: JSONContent) {
  const sections: { id: string; label: string }[] = [];
  const images = new Set<string>();
  function plainText(node: JSONContent): string {
    return node.text ?? (node.content?.map(plainText).join("") || "");
  }
  function visit(node: JSONContent): JSONContent {
    if (node.type === "image" && typeof node.attrs?.src === "string") images.add(node.attrs.src);
    if (node.type === "attachment" && node.attrs?.type === "image") images.add(node.attrs.url);
    if (node.type === "heading") {
      const label = plainText(node).trim();
      if (label) {
        const id = `section-${sections.length + 1}`;
        sections.push({ id, label });
        return { ...node, attrs: { ...node.attrs, sectionId: id } };
      }
    }
    return node.content ? { ...node, content: node.content.map(visit) } : node;
  }
  return { document: visit(body), sections, images };
}

function ArticleAuthors({ authors }: { authors: ProfileCard[] }) {
  const { user } = useApp();
  const [author, ...featured] = authors;
  const username = author?.username;
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

  if (!author) return null;
  return <aside className="reader-author" aria-label="About the authors">
    <Link to={`/@${author.username}`}><Avatar src={author.avatars.original} name={author.display_name} size="md" /></Link>
    <div>
      <p className="eyebrow">Written by</p>
      <h2><Link to={`/@${author.username}`}>{author.display_name}</Link></h2>
      {profile?.bio && <p className="author-bio">{profile.bio}</p>}
      <p className="author-details">{profile?.location && `${profile.location} · `}@{author.username}</p>
      {featured.length > 0 && <p className="author-details">With {featured.map((person, index) => <span key={person.id}>
        {index > 0 && ", "}<Link to={`/@${person.username}`}>{person.display_name}</Link>
      </span>)}</p>}
      {profile && user && profile.id !== user.id && <button className="button-secondary reader-follow" disabled={busy}
        aria-pressed={profile.is_following} onClick={() => void toggleFollow()}>{profile.is_following ? "Following" : "Follow"}</button>}
      {error && <p role="alert" className="notice-error">{error}</p>}
    </div>
  </aside>;
}

function ArticleDates({ article }: { article: Article }) {
  if (!article.published_at) return <span className="article-timestamps">{article.status === "scheduled" && article.scheduled_at
    ? `Scheduled for ${new Date(article.scheduled_at).toLocaleString()}` : "Private draft"}</span>;
  return <span className="article-timestamps">
    <time dateTime={article.published_at} title={article.pinned_at ? `Pinned ${exactDateTime(article.pinned_at)}` : undefined}>{publicationDate(article.published_at)}</time>
    {Date.parse(article.updated_at) > Date.parse(article.published_at) && <> (updated at{" "}
      <time dateTime={article.updated_at}>{publicationDate(article.updated_at)}</time>)</>}
  </span>;
}

function SectionNavigation({ sections }: { sections: ReturnType<typeof readingSections>["sections"] }) {
  const [current, setCurrent] = useState<string | undefined>();
  useEffect(() => {
    if (!sections.length) return;
    function update() {
      const active = sections.filter(({ id }) => {
        const section = document.getElementById(id);
        return section && section.getBoundingClientRect().top < 150;
      }).at(-1);
      setCurrent(active?.id ?? sections[0].id);
    }
    update();
    window.addEventListener("scroll", update, { passive: true });
    window.addEventListener("resize", update);
    return () => {
      window.removeEventListener("scroll", update);
      window.removeEventListener("resize", update);
    };
  }, [sections]);
  return sections.length > 0 && <nav className="section-nav" aria-label="Article sections">
    {sections.map(({ id, label }) => <a href={`#${id}`} key={id} aria-label={label}
      title={label} aria-current={id === current ? "location" : undefined}><span>{label}</span></a>)}
  </nav>;
}

export function ArticlePresentation({ article, owner, onChanged }: {
  article: Article; owner: boolean; onChanged?: (article: Article) => void;
}) {
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState("");
  const [comments, setComments] = useState(true);
  const [focusReply, setFocusReply] = useState(false);
  const { hash } = useLocation();
  const { document, sections, images } = useMemo(() => readingSections(article.body), [article.body]);

  useEffect(() => {
    if (hash.startsWith("#comment-")) setComments(true);
  }, [hash]);

  async function share() {
    try {
      await navigator.clipboard.writeText(new URL(article.share_url ?? `/articles/${article.id}`, window.location.origin).toString());
      setCopied(true);
    } catch (reason) { setError(errorMessage(reason)); }
  }

  return <article className="reader">
    <a className="skip-link" href="#article">Skip to article</a>
    <header className="reader-hero">
      {article.thumbnail_url && <figure className="article-cover"><img src={article.thumbnail_url} alt="" /></figure>}
      <div className="reader-meta">
        {owner && <Link to={`/articles/${article.id}/edit`} className="text-link"><Icon name="write" width={14} height={14} /> Edit article</Link>}
        <ArticleDates article={article} />
        <PublicationStatus pinnedAt={article.pinned_at} archivedAt={article.archived_at} />
        {owner && <PublicationMenu item={article} onReconciled={(updated) => {
          if (updated.kind === "article") onChanged?.(updated);
        }} onChanged={(updated) => {
          if (updated.kind === "article") onChanged?.(updated);
        }}><Link to={`/articles/${article.id}/edit`}>Edit article</Link></PublicationMenu>}
      </div>
      <h1>{article.title}</h1>
      {article.summary && <p className="reader-deck">{article.summary}</p>}
    </header>
    <SectionNavigation sections={sections} />
    <div className="reading-prose" id="article">
      <TipTapDocument body={document} />
      <Attachments items={article.attachments.filter((item) => item.type !== "image" || !images.has(item.url))} />
    </div>
    <div className="reader-end">
      <div className="end-mark" aria-hidden="true"><i /><i /><i /></div>
      <div className="reader-end-date"><ArticleDates article={article} /></div>
      <ArticleAuthors authors={article.authors} />
      {error && <p className="notice-error" role="alert">{error}</p>}
      {article.status === "published" && !article.archived_at && <>
        <PublicationActions kind="article" id={article.id} onComments={() => { setFocusReply(!comments); setComments(!comments); }}
          commentsOpen={comments} onShare={() => void share()} copied={copied} />
        <div hidden={!comments}>
          <Discussion key={article.id} kind="article" id={article.id} deepLink focusComposer={comments && focusReply} />
        </div>
      </>}
      {article.archived_at && <Discussion key={article.id} kind="article" id={article.id} deepLink readOnly />}
      <Footer reading />
    </div>
  </article>;
}
