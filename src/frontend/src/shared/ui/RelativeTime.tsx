import { exactDateTime, relativeDate } from "./dates";

export function RelativeTime({ publishedAt, updatedAt, repostedAt, pinnedAt, archivedAt }: {
  publishedAt: string;
  updatedAt?: string | null;
  repostedAt?: string;
  pinnedAt?: string | null;
  archivedAt?: string | null;
}) {
  const eventAt = repostedAt ?? publishedAt;
  const details = [`Published ${exactDateTime(publishedAt)}`];
  if (repostedAt) details.unshift(`Reposted ${exactDateTime(repostedAt)}`);
  if (pinnedAt) details.push(`Pinned ${exactDateTime(pinnedAt)}`);
  if (archivedAt) details.push(`Archived ${exactDateTime(archivedAt)}`);
  if (updatedAt && Date.parse(updatedAt) !== Date.parse(publishedAt)) {
    details.push(`Updated ${exactDateTime(updatedAt)}`);
  }
  return <time dateTime={eventAt} title={details.join("\n")}>{relativeDate(eventAt)}</time>;
}
