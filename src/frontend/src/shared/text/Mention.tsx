import { Link } from "react-router-dom";
import { useProfileCard } from "../api/profileCards";

export function Mention({ userId, editable = false }: { userId: string; editable?: boolean }) {
  const profile = useProfileCard(userId);
  if (!profile) return <span className="mention-unavailable">{profile === undefined ? "Loading mention…" : "Account unavailable"}</span>;
  return editable ? <span className="content-link mention">@{profile.username}</span>
    : <Link className="content-link mention" to={`/@${profile.username}`}>@{profile.username}</Link>;
}
