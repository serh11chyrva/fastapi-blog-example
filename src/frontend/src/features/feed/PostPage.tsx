import { useApp } from "../../app/AuthProvider";
import { useParams } from "react-router-dom";
import { PostDetail } from "./PostDetail";

export function PostPage() {
  const { user } = useApp();
  const { postId = "" } = useParams();
  return <PostDetail key={`${postId}:${user?.id ?? "anonymous"}`} postId={postId} />;
}
