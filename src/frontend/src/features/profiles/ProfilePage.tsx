import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";
import { useApp } from "../../app/AuthProvider";
import { usePageTitle } from "../../app/usePageTitle";
import { api, errorMessage } from "../../shared/api/client";
import type { Profile, ProfileCard, ProfileLink } from "../../shared/api/types";
import { useOffsetList } from "../../shared/hooks/useOffsetList";
import { Avatar } from "../../shared/ui/Avatar";
import { EmptyState } from "../../shared/ui/EmptyState";
import { Icon } from "../../shared/ui/Icon";
import { publicationEvent } from "../interactions/events";
import { BadgeIcon } from "./BadgeIcon";
import { ProfilePublications } from "./ProfilePublications";
import { ProfileTimeline } from "./ProfileTimeline";

function PublicLink({ link }: { link: ProfileLink }) {
  return <a className="profile-external-link" href={link.redirect_url} target="_blank" rel="noreferrer">
    <Icon name="link" width={15} height={15} /><span>{link.label}</span>
    <Icon name="external" width={12} height={12} className="external-indicator" />
  </a>;
}

export function ProfilePage() {
  const { handle = "" } = useParams();
  return <ProfileContent key={handle} username={handle.replace(/^@/, "")} />;
}

function ProfileContent({ username }: { username: string }) {
  const { user } = useApp();
  const location = useLocation();
  const profilePath = `/users/${encodeURIComponent(username)}`;
  const [profile, setProfile] = useState<Profile | null>(null);
  const [error, setError] = useState("");
  const [actionError, setActionError] = useState("");
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState(false);
  const [tab, setTab] = useState<"posts" | "articles">("posts");
  const [refreshKey, setRefreshKey] = useState(0);
  const [networkKind, setNetworkKind] = useState<"followers" | "following" | null>(null);
  const linksDialog = useRef<HTMLDialogElement>(null);
  const networkDialog = useRef<HTMLDialogElement>(null);
  const network = useOffsetList<ProfileCard>(networkKind ? `${profilePath}/${networkKind}` : null);

  useEffect(() => {
    const controller = new AbortController();
    setError("");
    api<Profile>(profilePath, { signal: controller.signal })
      .then((value) => { if (!controller.signal.aborted) setProfile(value); })
      .catch((reason: unknown) => { if (!controller.signal.aborted) setError(errorMessage(reason)); });
    return () => controller.abort();
  }, [profilePath, user?.id]);

  const refreshActivity = useCallback(() => {
    setRefreshKey((value) => value + 1);
  }, []);

  useEffect(() => {
    if (profile?.id !== user?.id || !user) return;
    window.addEventListener(publicationEvent, refreshActivity);
    return () => window.removeEventListener(publicationEvent, refreshActivity);
  }, [profile?.id, user, refreshActivity]);

  async function toggleFollow() {
    if (!profile || busy) return;
    setBusy(true);
    setActionError("");
    try {
      await api(`${profilePath}/follow`, { method: profile.is_following ? "DELETE" : "PUT" });
      setProfile(await api<Profile>(profilePath));
    } catch (reason) {
      setActionError(errorMessage(reason));
    } finally {
      setBusy(false);
    }
  }

  async function share() {
    try {
      await navigator.clipboard.writeText(new URL(location.pathname, window.location.origin).toString());
      setCopied(true);
      setActionError("");
    } catch (reason) { setActionError(errorMessage(reason)); }
  }

  function showNetwork(kind: "followers" | "following") {
    setNetworkKind(kind);
    networkDialog.current?.showModal();
  }

  usePageTitle(error && !profile ? "Profile unavailable" : profile?.display_name ?? "Loading profile");
  if (!profile) return error
    ? <EmptyState title="Profile unavailable" body={error} />
    : <p className="list-status" role="status">Loading profile…</p>;

  const own = user?.id === profile.id;
  const authReturn = { from: location.pathname };
  return <>
    <section className="profile-section" aria-label="Profile">
      <div className="profile-cover">
        {profile.banner_url && <img src={profile.banner_url} alt="" />}
      </div>
      <div className="profile-details">
        <div className="profile-controls">
          <div className="profile-portrait"><Avatar src={profile.avatars.original} name={profile.display_name} size="lg" /></div>
          <div className="profile-actions">
            <button type="button" className="icon-button profile-share" aria-label={copied ? "Profile link copied" : "Share profile"}
              title={copied ? "Link copied" : "Share profile"} onClick={() => void share()}>
              <Icon name={copied ? "check" : "share"} />
            </button>
            {own ? <Link to="/settings/profile" className="button-secondary">Edit profile</Link> : user
              ? <button className={profile.is_following ? "button-secondary" : "button-primary"} disabled={busy}
                  aria-pressed={profile.is_following} onClick={() => void toggleFollow()}>
                  {profile.is_following ? "Following" : "Follow"}
                </button>
              : <Link className="button-primary" to="/login" state={authReturn}>Sign in to follow</Link>}
          </div>
        </div>
        <h1>{profile.display_name}</h1>
        <p className="profile-handle">@{profile.username}</p>
        <div className="profile-bio-grid">
          <div>
            {profile.bio && <p className="profile-bio-copy">{profile.bio}</p>}
            {profile.badges.length > 0 && <div className="profile-badges">
              {profile.badges.map((badge) => <span className="badge" key={badge.code}
                title={badge.payload.description ?? undefined} style={{ backgroundColor: badge.payload.background_color, color: badge.payload.text_color }}>
                <BadgeIcon badge={badge} />{badge.payload.label}
              </span>)}
            </div>}
            <div className="profile-bio-meta">
              {profile.location && <span><Icon name="pin" width={14} height={14} />{profile.location}</span>}
              {profile.joined_at && <span><Icon name="calendar" width={14} height={14} />
                <time dateTime={profile.joined_at}>Joined {new Date(profile.joined_at).toLocaleDateString("en", { month: "long", year: "numeric" })}</time>
              </span>}
            </div>
            <div className="profile-counts">
              <button type="button" onClick={() => showNetwork("followers")}>
                <strong>{profile.follower_count.toLocaleString("en")}</strong> followers
              </button>
              <button type="button" onClick={() => showNetwork("following")}>
                <strong>{profile.following_count.toLocaleString("en")}</strong> following
              </button>
            </div>
          </div>
          {profile.links.length > 0 && <div className="profile-links">
            {profile.links.slice(0, 3).map((link) => <PublicLink key={link.id} link={link} />)}
            {profile.links.length > 3 && <button type="button" className="text-link"
              onClick={() => linksDialog.current?.showModal()}>and {profile.links.length - 3} more…</button>}
          </div>}
        </div>
        {actionError && <p className="notice-error" role="alert">{actionError}</p>}
        {copied && <span className="sr-only" role="status">Profile link copied.</span>}
      </div>
    </section>
    <div className="rich-tabs" role="tablist" aria-label="Profile sections">
      {(["posts", "articles"] as const).map((kind) => <button key={kind} type="button" role="tab" id={`tab-${kind}`}
        aria-controls={`panel-${kind}`} aria-selected={tab === kind} tabIndex={tab === kind ? 0 : -1}
        onClick={() => setTab(kind)} onKeyDown={(event) => {
          if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
          event.preventDefault();
          const next = event.key === "Home" ? "posts" : event.key === "End" ? "articles" : kind === "posts" ? "articles" : "posts";
          setTab(next);
          document.getElementById(`tab-${next}`)?.focus();
        }}>
        {kind === "posts" ? "Posts" : "Articles"}
      </button>)}
    </div>
    <section id={`panel-${tab}`} role="tabpanel" aria-labelledby={`tab-${tab}`}>
      {tab === "posts"
        ? <ProfileTimeline key={`${profile.username}-${refreshKey}`} username={profile.username} onChanged={refreshActivity} />
        : <ProfilePublications key={profile.username} username={profile.username} />}
    </section>
    <dialog className="design-dialog" ref={linksDialog}>
      <div className="dialog-heading"><h2>All links</h2>
        <button type="button" className="icon-button" aria-label="Close links" onClick={() => linksDialog.current?.close()}><Icon name="close" /></button>
      </div>
      <div className="dialog-body profile-links">{profile.links.map((link) => <PublicLink key={link.id} link={link} />)}</div>
    </dialog>
    <dialog className="design-dialog" ref={networkDialog} onClose={() => setNetworkKind(null)}>
      <div className="dialog-heading"><h2>{networkKind === "followers" ? "Followers" : "Following"}</h2>
        <button type="button" className="icon-button" aria-label="Close profiles" onClick={() => networkDialog.current?.close()}><Icon name="close" /></button>
      </div>
      <div className="dialog-body profile-links">
        {network.items.map((person) => <Link className="discovery-person" to={`/@${person.username}`} key={person.id}
          onClick={() => networkDialog.current?.close()}>
          <Avatar src={person.avatars.original} name={person.display_name} size="sm" />
          <span><strong>{person.display_name}</strong><small>@{person.username}</small></span>
        </Link>)}
        {network.loading && <p role="status">Loading profiles…</p>}
        {network.error && <p className="notice-error" role="alert">{network.error}</p>}
        {!network.loading && !network.error && !network.items.length && <p>No profiles to show.</p>}
        {network.hasMore && <button type="button" className="button-secondary" disabled={network.loading}
          onClick={() => void network.loadMore()}>Load more profiles</button>}
      </div>
    </dialog>
  </>;
}
