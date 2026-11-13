import { InlineText } from "../../shared/text/InlineText";

export function PostText({ text }: { text: string }) {
  return <p className="post-copy"><InlineText text={text} /></p>;
}
