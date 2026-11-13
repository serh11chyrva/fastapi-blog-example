import { Link, useLocation } from "react-router-dom";
import { useEffect, useRef } from "react";
import { useApp } from "../../app/AuthProvider";
import type { PublicationKind } from "../../shared/api/types";
import { ReplyList } from "./ReplyThread";

export function Discussion({
  kind, id, deepLink = false, focusComposer = false, readOnly = false, visible = true,
}: {
  kind: PublicationKind; id: string; deepLink?: boolean; focusComposer?: boolean; readOnly?: boolean; visible?: boolean;
}) {
  const { user } = useApp();
  const location = useLocation();
  const section = useRef<HTMLElement>(null);
  useEffect(() => {
    if (location.hash === "#replies") section.current?.scrollIntoView({ block: "start" });
  }, [location.key, location.hash]);
  const commentId = deepLink && kind === "article" ? /^#comment-([0-9a-f]{24})$/i.exec(location.hash)?.[1] : undefined;
  return <section ref={section} id="replies" className="discussion" aria-label={kind === "micro_post" ? "Post replies" : "Article comments"}>
    {readOnly && <p className="list-status">This discussion is read only.</p>}
    {!readOnly && !user && <p className="discussion-signin"><Link className="text-link" to="/login"
      state={{ from: location.pathname + location.search + location.hash }}>Sign in</Link> to join the conversation.</p>}
    <ReplyList key={`${kind}:${id}:${user?.id ?? "anonymous"}`} kind={kind} id={id} commentId={commentId}
      readOnly={readOnly} focusComposer={focusComposer || location.hash === "#replies"} visible={visible} />
  </section>;
}

