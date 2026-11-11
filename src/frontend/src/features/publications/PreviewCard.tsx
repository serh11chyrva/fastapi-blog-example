import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import type { ArticleFeedItem, PublicationPreview } from "../../shared/api/types";
import { Avatar } from "../../shared/ui/Avatar";
import { Icon } from "../../shared/ui/Icon";
import { publicationDate } from "../../shared/ui/dates";
import { RelativeTime } from "../../shared/ui/RelativeTime";

function ArticleExcerpt({ text }: { text: string }) {
  const element = useRef<HTMLParagraphElement>(null);
  const [overflow, setOverflow] = useState(false);
  useEffect(() => {
    let active = true;
    const update = () => {
      if (active && element.current) setOverflow(element.current.scrollHeight > element.current.clientHeight + 1);
    };
    const observer = new ResizeObserver(update);
    if (element.current) observer.observe(element.current);
    update();
    void document.fonts.ready.then(update);
    return () => { active = false; observer.disconnect(); };
  }, [text]);
  return <p ref={element} className="article-excerpt" data-overflow={overflow}>{text}</p>;
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
  return <Link className={`longread-card ${standalone ? "longread-standalone" : ""}`} to={href}>
    {item.thumbnail_url && <div className="longread-cover">
      <img className="longread-image" src={item.thumbnail_url} alt="" loading="lazy" />
    </div>}
    <div className="longread-copy">
      <h2>{item.title}</h2>
      <time dateTime={item.published_at}>{publicationDate(item.published_at)}</time>
      {item.summary && <ArticleExcerpt text={item.summary} />}
      <span className="longread-link">Read article <Icon name="right" width={13} height={13} /></span>
    </div>
  </Link>;
}
