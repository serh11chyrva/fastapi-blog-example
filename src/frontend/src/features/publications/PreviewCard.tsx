import { Link } from "react-router-dom";
import type { ArticleFeedItem, PublicationPreview } from "../../shared/api/types";
import { Avatar } from "../../shared/ui/Avatar";
import { Icon } from "../../shared/ui/Icon";
import { publicationDate } from "../../shared/ui/dates";
import { RelativeTime } from "../../shared/ui/RelativeTime";

function ArticleExcerpt({ text }: { text: string }) {
  return <div className="article-excerpt"><p>{text}</p></div>;
}

export function PreviewCard({ item, standalone = false }: {
  item: PublicationPreview | ArticleFeedItem;
  standalone?: boolean;
}) {
  const href = item.share_url ?? `/articles/${item.id}`;
  if (item.kind === "micro_post") {
    const author = item.authors[0];
    return <Link to={href} className="quote-card">
      {author && <div className="quote-byline"><Avatar name={author.display_name} src={author.avatars.original} size="sm" />
        <strong>{author.display_name}</strong>
        <span>@{author.username} · <RelativeTime publishedAt={item.published_at} updatedAt={item.updated_at} /></span>
      </div>}
      <p>{item.text}</p>
      {item.thumbnail_url && <img src={item.thumbnail_url} alt="" className="quote-image" loading="lazy" />}
    </Link>;
  }
  return <div className="card-surface article-surface">
    <article className={`longread-card ${standalone ? "longread-standalone" : ""}`}>
    {item.thumbnail_url && <Link className="longread-cover" to={href} aria-label={`Read ${item.title}`}>
      <img className="longread-image" src={item.thumbnail_url} alt="" loading="lazy" />
    </Link>}
    <div className="longread-body">
      <div className="longread-title-row">
        <h2><Link to={href}>{item.title}</Link></h2>
        <time dateTime={item.published_at}>{publicationDate(item.published_at)}</time>
      </div>
      {item.summary && <ArticleExcerpt text={item.summary} />}
      <div className="article-bottom">
        <Link className="article-read-button" to={href}>Read article <Icon name="right" width={18} height={18} /></Link>
      </div>
    </div>
    </article>
  </div>;
}
