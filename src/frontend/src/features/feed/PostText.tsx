import { Fragment } from "react";
import { Link } from "react-router-dom";
import { Icon } from "../../shared/ui/Icon";

export function PostText({ text }: { text: string }) {
  const tokens = /https?:\/\/[^\s<>]+|(?<![\p{L}\p{N}_])(?:@[a-z\d_]{3,24}|#[\p{L}\p{N}_]+)/giu;
  let end = 0;
  return <p className="post-copy">
    {[...text.matchAll(tokens)].map((match) => {
      const start = match.index;
      const before = text.slice(end, start);
      const value = match[0];
      end = start + value.length;
      if (value.startsWith("@")) return <Fragment key={start}>{before}<Link to={`/${value}`}>{value}</Link></Fragment>;
      if (value.startsWith("#")) return <Fragment key={start}>{before}<strong>{value}</strong></Fragment>;
      const url = value.replace(/[.,!?;:]+$/, "");
      return <Fragment key={start}>{before}<a href={url} target="_blank" rel="noreferrer">
        {url}<Icon name="external" width={13} height={13} />
      </a>{value.slice(url.length)}</Fragment>;
    })}
    {text.slice(end)}
  </p>;
}
