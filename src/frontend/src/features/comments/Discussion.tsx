import { Link, useLocation } from "react-router-dom";
import { useApp } from "../../app/AuthProvider";
import type { PublicationKind } from "../../shared/api/types";
import { ReplyList } from "./ReplyThread";

export function Discussion({ kind, id, deepLink = false, focusComposer = false }: {
  kind: PublicationKind; id: string; deepLink?: boolean; focusComposer?: boolean;
}) {
  const { user } = useApp();
  const location = useLocation();
  const commentId = deepLink && kind === "article" ? /^#comment-([0-9a-f]{24})$/i.exec(location.hash)?.[1] : undefined;
  return <section className="discussion" aria-label={kind === "micro_post" ? "Post replies" : "Article comments"}>
    {!user && <p className="discussion-signin"><Link className="text-link" to="/login"
      state={{ from: location.pathname + location.search + location.hash }}>Sign in</Link> to join the conversation.</p>}
    <ReplyList key={`${kind}:${id}:${user?.id ?? "anonymous"}`} kind={kind} id={id} commentId={commentId}
      focusComposer={focusComposer} />
  </section>;
}

