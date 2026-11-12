import { useApp } from "../../app/AuthProvider";
import { usePageTitle } from "../../app/usePageTitle";
import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api, errorMessage } from "../../shared/api/client";
import type { MicroPost } from "../../shared/api/types";
import { EmptyState } from "../../shared/ui/EmptyState";
import { FeedCard } from "./FeedCard";

export function PostPage() {
  const { user } = useApp();
  const { postId = "" } = useParams();
  return <PostContent key={`${postId}:${user?.id ?? "anonymous"}`} postId={postId} />;
}

function PostContent({ postId }: { postId: string }) {
  const { user } = useApp();
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
  }, [postId, version, user?.id]);
  usePageTitle(error ? "Post unavailable" : post ? `Post by ${post.authors[0]?.display_name ?? "Unknown author"}` : "Loading post");
  if (post?.archived_at && user?.id !== post.owner_id) return <p role="status">Loading post…</p>;
  if (error) return <EmptyState title="Note unavailable" body={error} />;
  if (!post) return <p role="status">Loading note…</p>;
  return <div className="post-detail"><FeedCard key={post.id}
    item={{ ...post, published_at: post.created_at }} showDiscussion onChanged={() => setVersion((value) => value + 1)} />
  </div>;
}
