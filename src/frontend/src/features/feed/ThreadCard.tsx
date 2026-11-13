import { Link } from "react-router-dom";
import type { FeedItem, ThreadPart } from "../../shared/api/types";
import { FeedCard } from "./FeedCard";
import { TombstoneCard } from "./TombstoneCard";

export function ThreadPartCard({ part, onChanged }: { part: ThreadPart; onChanged: () => void }) {
  return part.kind === "deleted_reply" ? <TombstoneCard post={part} />
    : <FeedCard item={part} onChanged={onChanged} showContext={false} />;
}

export function ThreadCard({ item, onChanged }: { item: FeedItem; onChanged: () => void }) {
  const preview = item.kind === "micro_post" ? item.thread_preview : null;
  if (!preview?.parts.length) return <FeedCard item={item} onChanged={onChanged} />;
  return <section className="author-thread" aria-label="Author thread">
    <div className="thread-parts">
      <FeedCard item={item} onChanged={onChanged} showContext={false} />
      {preview.parts.map((part) => <div key={part.id}><ThreadPartCard part={part} onChanged={onChanged} /></div>)}
    </div>
    <Link className="thread-link" to={`/posts/${item.id}/thread`}>{preview.has_more ? "View full thread" : "View thread"}</Link>
  </section>;
}
