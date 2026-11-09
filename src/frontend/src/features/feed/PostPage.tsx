import { usePageTitle } from "../../app/usePageTitle";
import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api, errorMessage } from "../../shared/api/client";
import type { MicroPost } from "../../shared/api/types";
import { EmptyState } from "../../shared/ui/EmptyState";
import { FeedCard } from "./FeedCard";

export function PostPage() {
  const { postId = "" } = useParams();
  return <PostContent key={postId} postId={postId} />;
}

function PostContent({ postId }: { postId: string }) {
  const [post, setPost] = useState<MicroPost | null>(null);
  const [error, setError] = useState("");
  const [version, setVersion] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setPost(null);
    setError("");
    api<MicroPost>(`/posts/${encodeURIComponent(postId)}`, { signal: controller.signal })
      .then((value) => { if (!controller.signal.aborted) setPost(value); })
      .catch((reason: unknown) => { if (!controller.signal.aborted) setError(errorMessage(reason)); });
    return () => controller.abort();
  }, [postId, version]);
  usePageTitle(error ? "Post unavailable" : post ? `Post by ${post.authors[0]?.display_name ?? "Unknown author"}` : "Loading post");
  if (error) return <EmptyState title="Note unavailable" body={error} />;
  if (!post) return <p role="status">Loading note…</p>;
  return <div className="mx-auto max-w-2xl"><FeedCard key={post.id}
    item={{ ...post, published_at: post.created_at }} showDiscussion onChanged={() => setVersion((value) => value + 1)} />
  </div>;
}
