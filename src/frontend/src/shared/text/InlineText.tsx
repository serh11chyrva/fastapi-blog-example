import { Fragment } from "react";
import { Link } from "react-router-dom";
import { inlineLinkTokens } from "./hashtags";

export function InlineText({ text }: { text: string }) {
  let end = 0;
  return <>{inlineLinkTokens(text).map(({ start, end: next, value, kind, href }) => {
    const before = text.slice(end, start);
    end = next;
    const className = `content-link ${kind === "external" ? "external-link" : kind}`;
    return <Fragment key={start}>{before}{kind === "external"
      ? <a className={className} href={href} target="_blank" rel="noopener noreferrer nofollow">{value}</a>
      : <Link className={className} to={href}>{value}</Link>}</Fragment>;
  })}{text.slice(end)}</>;
}
