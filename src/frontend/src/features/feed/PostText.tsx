import { Fragment } from "react";
import { Link } from "react-router-dom";
import { Icon } from "../../shared/ui/Icon";
import { hashtagHref, inlineTokens } from "../../shared/text/hashtags";

export function PostText({ text }: { text: string }) {
  let end = 0;
  return <p className="post-copy">
    {inlineTokens(text).map((match) => {
      const start = match.start;
      const before = text.slice(end, start);
      const value = match.value;
      end = start + value.length;
      if (value.startsWith("@")) return <Fragment key={start}>{before}<Link to={`/${value}`}>{value}</Link></Fragment>;
      if (value.startsWith("#")) return <Fragment key={start}>{before}{[...value.slice(1)].length <= 64
        ? <Link className="hashtag" to={hashtagHref(value.slice(1))}>{value}</Link> : value}</Fragment>;
      const url = value.replace(/[.,!?;:]+$/, "");
      return <Fragment key={start}>{before}<a href={url} target="_blank" rel="noreferrer">
        {url}<Icon name="external" width={13} height={13} />
      </a>{value.slice(url.length)}</Fragment>;
    })}
    {text.slice(end)}
  </p>;
}
