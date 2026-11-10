import { Link } from "react-router-dom";
import type { ArticleFeedItem, PublicationPreview } from "../../shared/api/types";
import { Avatar } from "../../shared/ui/Avatar";
import { Icon } from "../../shared/ui/Icon";
import { publicationDate } from "../../shared/ui/dates";
import { RelativeTime } from "../../shared/ui/RelativeTime";

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
  return <Link className={`longread-card ${standalone ? "longread-standalone" : ""}`} to={href}>
    {item.thumbnail_url && <img className="longread-image" src={item.thumbnail_url} alt="" loading="lazy" />}
    <div className="longread-copy">
      <h2>{item.title}</h2>
      <time dateTime={item.published_at}>{publicationDate(item.published_at)}</time>
      {item.summary && <p>{item.summary}</p>}
      <span className="longread-link">Read article <Icon name="right" width={13} height={13} /></span>
    </div>
  </Link>;
}
