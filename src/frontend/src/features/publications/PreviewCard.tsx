import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { PublicationMenu } from "./PublicationMenu";
import { PublicationStatus } from "./PublicationStatus";
import { useApp } from "../../app/AuthProvider";
import type { Article, ArticleFeedItem, MicroPost, PublicationPreview } from "../../shared/api/types";
import { Avatar } from "../../shared/ui/Avatar";
import { Icon } from "../../shared/ui/Icon";
import { exactDateTime, publicationDate } from "../../shared/ui/dates";
import { RelativeTime } from "../../shared/ui/RelativeTime";
import { HashtagText } from "../../shared/text/HashtagText";

function ArticleExcerpt({ text }: { text: string }) {
  return <div className="article-excerpt"><p><HashtagText text={text} /></p></div>;
}

export function PreviewCard({ item: initialItem, standalone = false, onChanged, excerpt }: {
  item: PublicationPreview | ArticleFeedItem;
  standalone?: boolean;
  onChanged?: () => void;
  excerpt?: string | null;
}) {
  const { user } = useApp();
  const [item, setItem] = useState(initialItem);
  useEffect(() => { setItem(initialItem); }, [initialItem]);
  function reconcile(updated: Article | MicroPost) {
    if (updated.kind === "article") setItem({ ...updated, published_at: updated.published_at ?? initialItem.published_at });
  }
  const href = item.share_url ?? `${item.kind === "micro_post" ? "/posts" : "/articles"}/${item.id}`;
  if (item.kind === "micro_post") {
    const author = item.authors[0];
    return <div className="quote-card">
      {author && <div className="quote-byline"><Link to={`/@${author.username}`}>
        <Avatar name={author.display_name} src={author.avatars.original} size="sm" /></Link>
        <strong><HashtagText text={author.display_name} href={`/@${author.username}`} /></strong>
        <span>@{author.username} · <RelativeTime publishedAt={item.published_at} updatedAt={item.updated_at} /></span>
      </div>}
      <p><HashtagText text={item.text} href={href} /></p>
      {item.thumbnail_url && <Link to={href}><img src={item.thumbnail_url} alt="" className="quote-image" loading="lazy" /></Link>}
      <Link className="text-link quote-open" to={href}>View post <Icon name="right" width={13} height={13} /></Link>
    </div>;
  }
  return <div className={`card-surface article-surface${standalone ? " motion-enter" : ""}`}>
    <article className={`longread-card ${standalone ? "longread-standalone" : ""}`}>
    {item.thumbnail_url && <Link className="longread-cover" to={href} aria-label={`Read ${item.title}`}>
      <img className="longread-image" src={item.thumbnail_url} alt="" loading="lazy" />
    </Link>}
    <div className="longread-body">
      <div className="longread-title-row">
        <h2><HashtagText text={item.title} href={href} /></h2>
        <time dateTime={item.published_at}
          title={"pinned_at" in item && item.pinned_at ? `Pinned ${exactDateTime(item.pinned_at)}` : undefined}>
          {publicationDate(item.published_at)}
        </time>
        {standalone && "owner_id" in item && user?.id === item.owner_id &&
          <PublicationMenu item={item} onChanged={() => onChanged?.()} onReconciled={reconcile}>
            <Link to={`/articles/${item.id}/edit`}>Edit article</Link>
          </PublicationMenu>}
      </div>
      {standalone && "owner_id" in item && <PublicationStatus pinnedAt={item.pinned_at} archivedAt={item.archived_at} />}
      {(excerpt ?? item.summary) && <ArticleExcerpt text={excerpt ?? item.summary} />}
      <div className="article-bottom">
        <Link className="article-read-button" to={href}>Read article <Icon name="right" width={18} height={18} /></Link>
      </div>
    </div>
    </article>
  </div>;
}
