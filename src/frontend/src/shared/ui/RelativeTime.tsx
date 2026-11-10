import { exactDateTime, relativeDate } from "./dates";

export function RelativeTime({ publishedAt, updatedAt, repostedAt }: {
  publishedAt: string;
  updatedAt?: string | null;
  repostedAt?: string;
}) {
  const eventAt = repostedAt ?? publishedAt;
  const details = [`Published ${exactDateTime(publishedAt)}`];
  if (repostedAt) details.unshift(`Reposted ${exactDateTime(repostedAt)}`);
  if (updatedAt && Date.parse(updatedAt) !== Date.parse(publishedAt)) {
    details.push(`Updated ${exactDateTime(updatedAt)}`);
  }
  return <time dateTime={eventAt} title={details.join("\n")}>{relativeDate(eventAt)}</time>;
}
