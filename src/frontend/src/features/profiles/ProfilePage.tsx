import { Link, useParams } from "react-router-dom";
import { useApp } from "../../app/AuthProvider";
import { useEffect, useState } from "react";
import type { Profile, ProfileCard } from "../../shared/api/types";
import { useOffsetList } from "../../shared/hooks/useOffsetList";
import { api, errorMessage } from "../../shared/api/client";
import { EmptyState } from "../../shared/ui/EmptyState";
import { Avatar } from "../../shared/ui/Avatar";
import { BadgeIcon } from "./BadgeIcon";
import { PostComposer } from "../feed/PostComposer";
import { ProfilePublications } from "./ProfilePublications";
export function ProfilePage() {
  const { handle } = useParams();
  return <ProfileContent key={handle} />;
}
function ProfileContent() {
  const { handle = "" } = useParams();
  const username = handle.replace(/^@/, "");
  const { user } = useApp();
  const [profile, setProfile] = useState<Profile | null>(null);
  const [error, setError] = useState("");
  const [tab, setTab] = useState<"micro_post" | "article">("micro_post");
  const [refreshKey, setRefreshKey] = useState(0);
  const [networkKind, setNetworkKind] = useState<"followers" | "following" | null>(null);
  const networkList = useOffsetList<ProfileCard>(networkKind && profile ? `/users/${profile.username}/${networkKind}` : null);
  const network = networkKind ? networkList.items : null;
  useEffect(() => {
    const controller = new AbortController();
    setProfile(null);
    setError("");
    setNetworkKind(null);
    api<Profile>(`/users/${encodeURIComponent(username)}`, { signal: controller.signal })
      .then((value) => {
        if (!controller.signal.aborted)
          setProfile(value);
      })
      .catch((reason: unknown) => {
        if (!controller.signal.aborted)
          setError(reason instanceof Error ? reason.message : "Could not load this page.");
      });
    return () => controller.abort();
  }, [username]);
  async function toggleFollow() {
    if (!profile)
      return;
    try {
      await api(`/users/${profile.username}/follow`, { method: profile.is_following ? "DELETE" : "PUT" });
      setProfile(await api<Profile>(`/users/${profile.username}`));
    }
    catch (reason) {
      setError(errorMessage(reason));
    }
  }
  function showNetwork(kind: "followers" | "following") {
    setNetworkKind(kind);
  }
  if (error)
    return <EmptyState title="Profile unavailable" body={error} />;
  if (!profile)
    return <div className="surface p-8 text-center text-sm text-slate-500">Loading profile…</div>;
  const own = user?.id === profile.id;
  return <div className="space-y-5">
    <section className="surface overflow-hidden">
      <div className="h-20 bg-neutral-100" />
      <div className="px-5 pb-6 sm:px-7">
        <div className="-mt-10 flex flex-wrap items-end justify-between gap-4">
          <Avatar src={profile.avatar_url} name={profile.display_name} size="lg" />
          <div className="flex gap-2">
            {own ? <Link to="/settings/profile" className="button-secondary">Edit profile</Link> : user ? <button className={profile.is_following ? "button-secondary" : "button-primary"} onClick={toggleFollow}>
              {profile.is_following ? "Following" : "Follow"}
            </button> : <Link className="button-primary" to="/login">Log in to follow</Link>}
          </div>
        </div>
        <h1 className="editorial-title mt-4 text-3xl font-semibold text-black">
          {profile.display_name}
        </h1>
        <p className="text-sm text-slate-500">@{profile.username}</p>
        {profile.bio && <p className="mt-4 max-w-2xl whitespace-pre-wrap text-[15px] leading-7 text-slate-700">
          {profile.bio}
        </p>}
        <div className="mt-4 flex gap-5 text-sm">
          <button onClick={() => void showNetwork("following")}>
            <strong className="text-slate-900">
              {profile.following_count}
            </strong>{" "}
            <span className="text-slate-500">Following</span>
          </button>
          <button onClick={() => void showNetwork("followers")}>
            <strong className="text-slate-900">
              {profile.follower_count}
            </strong>{" "}
            <span className="text-slate-500">Followers</span>
          </button>
        </div>
        {network && <div className="mt-4 border-t border-slate-100 pt-4">
          <p className="mb-3 text-sm font-semibold text-slate-700">
            {networkKind === "followers" ? "Followers" : "Following"}
          </p>
          <div className="flex flex-wrap gap-3">
            {network.map((person) => <Link className="flex items-center gap-2 border border-slate-200 px-3 py-2" key={person.id} to={`/@${person.username}`}>
              <Avatar src={person.avatar_url} name={person.display_name} size="sm" />
              <span className="text-sm">
                {person.display_name}
              </span>
            </Link>)}
          </div>
          {networkList.loading && <p role="status">Loading profiles…</p>}
          {networkList.error && <div className="notice-error">
            {networkList.error}
          </div>}
          {networkList.hasMore && <button className="button-secondary mt-3" disabled={networkList.loading} onClick={() => void networkList.loadMore()}>Load more profiles</button>}
        </div>}
        {profile.links.length > 0 && <div className="mt-4 flex flex-wrap gap-2">
          {profile.links.map((link) => <a key={link.id} href={link.redirect_url} data-platform={link.platform} target="_blank" rel="noreferrer" className="pill">↗ {link.label}</a>)}
        </div>}
        {profile.badges.length > 0 && <div className="mt-4 flex flex-wrap gap-2">
          {profile.badges.map((badge) => <span className="badge gap-1.5" key={badge.code} title={badge.payload.description || undefined} style={{ backgroundColor: badge.payload.background_color, color: badge.payload.text_color }}>
            <BadgeIcon badge={badge} />
            {badge.payload.label}
          </span>)}
        </div>}
        {error && <p className="mt-3 text-sm text-slate-700">
          {error}
        </p>}
      </div>
    </section>
    <div className="flex gap-7 border-b border-neutral-200">
      <button className={`profile-tab ${tab === "micro_post" ? "active" : ""}`} onClick={() => setTab("micro_post")}>Posts</button>
      <button className={`profile-tab ${tab === "article" ? "active" : ""}`} onClick={() => setTab("article")}>Articles</button>
    </div>
    {tab === "micro_post" && own && <PostComposer onPosted={() => setRefreshKey((value) => value + 1)} />}
    <ProfilePublications key={`${profile.username}-${tab}-${refreshKey}`} username={profile.username} kind={tab} onChanged={() => setRefreshKey((value) => value + 1)} />
  </div>;
}
