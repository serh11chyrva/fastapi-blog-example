import { Link } from "react-router-dom";
import type { ProfileActivity } from "../../shared/api/types";
import { useCursorList } from "../../shared/hooks/useCursorList";
import { FeedCard } from "../feed/FeedCard";
import { PublicationAuthors } from "../publications/PublicationAuthors";
import { PreviewCard } from "../publications/PreviewCard";

function activityKey(item: ProfileActivity) {
  return `${item.kind}:${item.id}`;
}

export function ProfileTimeline({ username, onChanged }: { username: string; onChanged: () => void }) {
  const list = useCursorList<ProfileActivity>(`/users/${encodeURIComponent(username)}/timeline`, activityKey);
  return <div className="space-y-4">
    {list.items.map((item) => item.kind === "article_comment"
      ? <article className="surface p-5 sm:p-6" key={activityKey(item)}>
          <PublicationAuthors authors={[item.author]} />
          <Link className="mt-2 block text-sm text-neutral-500 underline" to={`${item.article.share_url}#comment-${item.id}`}>
            Commented on an article · <time dateTime={item.created_at}>{new Date(item.created_at).toLocaleString()}</time>
          </Link>
          <p className="mt-3 whitespace-pre-wrap break-words leading-7">{item.text}</p>
          <PreviewCard item={item.article} />
        </article>
      : <FeedCard key={activityKey(item)} item={item} onChanged={onChanged} />)}
    {list.loading && <p role="status">Loading activity…</p>}
    {list.error && <p className="notice-error" role="alert">{list.error}{" "}
      <button className="underline" onClick={list.cursor ? () => void list.loadMore() : list.refresh}>Retry</button>
    </p>}
    {!list.loading && !list.error && !list.items.length && !list.cursor &&
      <p className="surface p-6 text-sm text-neutral-500">No public activity yet.</p>}
    {list.cursor && <button className="button-secondary w-full" disabled={list.loading}
      onClick={() => void list.loadMore()}>Load more</button>}
  </div>;
}
