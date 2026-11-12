import { Fragment } from "react";
import { Link } from "react-router-dom";
import { hashtagHref, hashtagMatches } from "./hashtags";

export function HashtagText({ text, href, linkClassName }: {
  text: string; href?: string; linkClassName?: string;
}) {
  let end = 0;
  const ordinary = (value: string) => href && value
    ? <Link to={href} className={linkClassName}>{value}</Link> : value;
  return <>{hashtagMatches(text).map((match) => {
    const before = text.slice(end, match.start);
    end = match.end;
    return <Fragment key={match.start}>{ordinary(before)}
      <Link className="hashtag" to={hashtagHref(match.value.slice(1))}>{match.value}</Link>
    </Fragment>;
  })}{ordinary(text.slice(end))}</>;
}
