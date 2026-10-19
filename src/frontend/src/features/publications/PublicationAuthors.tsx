import { Link } from "react-router-dom";
import type { ProfileCard } from "../../shared/api/types";
import { Avatar } from "../../shared/ui/Avatar";

export function PublicationAuthors({ authors }: { authors: ProfileCard[] }) {
  return <div className="flex flex-wrap gap-x-4 gap-y-2">
    {authors.map((author, index) => <Link key={author.id} to={`/@${author.username}`} className="flex items-center gap-2">
      <Avatar src={author.avatars.original} name={author.display_name} size="sm" />
      <span><span className="block text-sm font-semibold">{author.display_name}</span>
        <span className="block text-xs text-neutral-500">@{author.username}{index > 0 ? " · Featured author" : ""}</span>
      </span>
    </Link>)}
  </div>;
}
