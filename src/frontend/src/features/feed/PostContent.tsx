import type { Attachment, ReplyMetadata } from "../../shared/api/types";
import { Attachments } from "../publications/Attachments";
import { PostText } from "./PostText";

export function PostContent({ text, attachments, reply, context = true }: {
  text: string; attachments: Attachment[]; reply?: ReplyMetadata | null; context?: boolean;
}) {
  return <>
    {text && <PostText text={text} />}
    <Attachments items={attachments.filter((item) => item.type !== "hashtag" && item.type !== "mention")} />
    {context && reply && <div className="reply-context">
      <Attachments items={[reply.kind === "article"
        ? { type: "article", article_id: reply.publication_id }
        : { type: "post", post_id: reply.publication_id }]} />
    </div>}
  </>;
}
