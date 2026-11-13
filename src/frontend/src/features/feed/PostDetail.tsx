import { useEffect, useRef, useState } from "react";
import { useLocation } from "react-router-dom";
import { usePageTitle } from "../../app/usePageTitle";
import { api, errorMessage } from "../../shared/api/client";
import type { ContextPost, PostContext } from "../../shared/api/types";
import { EmptyState } from "../../shared/ui/EmptyState";
import { ReplyList } from "../comments/ReplyThread";
import { PublicationPageSkeleton } from "../publications/PublicationSkeleton";
import { FeedCard } from "./FeedCard";
import { TombstoneCard } from "./TombstoneCard";

export function PostDetail({ postId }: { postId: string }) {
  const [context, setContext] = useState<PostContext | null>(null);
  const [error, setError] = useState("");
  const [version, setVersion] = useState(0);
  const selected = useRef<HTMLDivElement>(null);
  const location = useLocation();
  const loaded = !!context;
  const refresh = () => setVersion((value) => value + 1);

  useEffect(() => {
    const controller = new AbortController();
    setError("");
    api<PostContext>(`/posts/${encodeURIComponent(postId)}/context`, { signal: controller.signal, cache: "no-store" })
      .then((value) => { if (!controller.signal.aborted) setContext(value); })
      .catch((reason: unknown) => { if (!controller.signal.aborted) { setContext(null); setError(errorMessage(reason)); } });
    return () => controller.abort();
  }, [postId, version]);

  useEffect(() => {
    if (!loaded) return;
    const frame = requestAnimationFrame(() => {
      if (location.hash === "#replies") document.getElementById("replies")?.scrollIntoView({ block: "start" });
      else selected.current?.scrollIntoView({ block: "start" });
    });
    return () => cancelAnimationFrame(frame);
  }, [loaded, location.key, location.hash]);

  usePageTitle(error ? "Post unavailable" : context?.post.kind === "deleted_reply" ? "Deleted reply"
    : context ? `Post by ${context.post.authors[0]?.display_name ?? "Unknown author"}` : "Loading post");

  function card(post: ContextPost, focused = false) {
    return post.kind === "deleted_reply" ? <TombstoneCard post={post} selected={focused} />
      : <FeedCard item={{ ...post, published_at: post.created_at }} showContext={false}
        showDiscussion={focused} onChanged={refresh} />;
  }

  if (error) return <><EmptyState title="Post unavailable" body={error} />
    <button className="button-secondary" onClick={refresh}>Retry</button></>;
  if (!context) return <PublicationPageSkeleton kind="micro_post" />;
  return <div className="post-detail conversation">
    {(context.original || context.ancestors.length > 0) && <div className="conversation-ancestors" role="region" aria-label="Earlier conversation">
      {context.original && <FeedCard item={context.original} onChanged={refresh} showContext={false} />}
      {context.ancestors.map((post) => <div key={post.id}>{card(post)}</div>)}
    </div>}
    <div ref={selected} className="conversation-selected" role="region" aria-label="Selected post">{card(context.post, true)}</div>
    {context.post.kind === "deleted_reply" && <section className="discussion deleted-discussion" id="replies" aria-label="Post replies">
      <h2>Replies</h2>
      <ReplyList kind={context.post.reply.kind} id={context.post.reply.publication_id}
        parentId={context.post.id} readOnly={context.read_only} />
    </section>}
  </div>;
}
