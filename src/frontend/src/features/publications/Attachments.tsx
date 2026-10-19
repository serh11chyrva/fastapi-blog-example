import { Link } from "react-router-dom";
import type { Attachment } from "../../shared/api/types";

export function Attachments({ items }: { items: Attachment[] }) {
  if (!items.length) return null;
  return <div className="mt-4 space-y-3">
    {items.map((item, index) => <div key={index} className="min-w-0 break-words">
      {item.type === "image" ? <img className="max-h-[32rem] w-full bg-neutral-50 object-contain" src={item.url} alt={item.alt} loading="lazy" />
        : item.type === "article" ? <Link className="block border border-neutral-200 p-4 text-sm underline" to={`/articles/${item.article_id}`}>Read attached article →</Link>
        : item.type === "hashtag" ? <span className="pill">#{item.tag}</span>
        : item.type === "mention" ? <span className="pill" title={item.user_id}>Account mention · {item.user_id.slice(-6)}</span>
        : item.type === "og_card" ? <a href={item.url} target="_blank" rel="noopener noreferrer" className="block overflow-hidden border border-neutral-200">
          {item.image_url && <img src={item.image_url} alt="" loading="lazy" referrerPolicy="no-referrer" className="max-h-52 w-full object-cover" />}
          <span className="block p-4"><strong className="block">{item.title}</strong>
            <span className="mt-1 block text-sm text-neutral-600">{item.description}</span>
            <span className="mt-2 block text-xs text-neutral-500">{item.site_name || item.url} ↗</span>
          </span>
        </a>
        : <a className="block border border-neutral-200 p-3 text-sm underline" href={item.url} target="_blank" rel="noopener noreferrer">
          {item.type === "link" ? item.label || item.url : item.type === "embed" ? `Open on ${item.provider} ↗` : "Open video ↗"}
        </a>}
    </div>)}
  </div>;
}
