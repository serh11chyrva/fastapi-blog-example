import { Link } from "react-router-dom";
import type { PublicationPreview } from "../../shared/api/types";

export function PreviewCard({ item }: { item: PublicationPreview }) {
  return <Link className="mt-3 block overflow-hidden rounded border border-neutral-200 hover:border-neutral-400"
    to={item.share_url}>
    {item.thumbnail_url && <img className="max-h-48 w-full object-cover" src={item.thumbnail_url} alt="" loading="lazy" />}
    <div className="space-y-1 p-4">
      <p className="text-xs text-neutral-500">
        {item.authors.map((author) => author.display_name).join(", ")} ·{" "}
        <time dateTime={item.published_at}>{new Date(item.published_at).toLocaleDateString()}</time>
      </p>
      {item.kind === "article" ? <>
        <strong className="block text-lg">{item.title}</strong>
        {item.summary && <p className="line-clamp-3 text-sm text-neutral-600">{item.summary}</p>}
        <span className="text-sm font-semibold">Read article →</span>
      </> : <p className="whitespace-pre-wrap break-words text-sm">{item.text}</p>}
    </div>
  </Link>;
}
