import { exactDateTime } from "../../shared/ui/dates";
import { Icon } from "../../shared/ui/Icon";

export function PublicationStatus({ pinnedAt, archivedAt }: { pinnedAt?: string | null; archivedAt?: string | null }) {
  return <>
    {pinnedAt && <span className="post-activity publication-status" title={`Pinned ${exactDateTime(pinnedAt)}`}>
      <Icon name="pushpin" width={15} height={15} />
      <time dateTime={pinnedAt} tabIndex={0} title={`Pinned ${exactDateTime(pinnedAt)}`}>Pinned</time>
    </span>}
    {archivedAt && <span className="post-activity publication-status" title={`Archived ${exactDateTime(archivedAt)}`}>
      <Icon name="archive" width={15} height={15} />
      <time dateTime={archivedAt}>Archived {exactDateTime(archivedAt)}</time>
    </span>}
  </>;
}
