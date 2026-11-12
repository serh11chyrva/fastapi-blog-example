import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";
import { useApp } from "../../app/AuthProvider";
import { usePageTitle } from "../../app/usePageTitle";
import { api, errorMessage } from "../../shared/api/client";
import type { OriginalFeedItem, Profile, ProfileCard, ProfileLink } from "../../shared/api/types";
import { useOffsetList } from "../../shared/hooks/useOffsetList";
import { Avatar } from "../../shared/ui/Avatar";
import { EmptyState } from "../../shared/ui/EmptyState";
import { Icon } from "../../shared/ui/Icon";
import { publicationEvent, publicationStateEvent } from "../interactions/events";
import { BadgeIcon } from "./BadgeIcon";
import { ProfilePublications } from "./ProfilePublications";
import { ProfileArchive } from "./ProfileArchive";
import { ProfileTimeline } from "./ProfileTimeline";
import { HashtagText } from "../../shared/text/HashtagText";
import { PeopleSkeleton } from "../../shared/ui/PeopleSkeleton";
import { PublicationListSkeleton } from "../publications/PublicationSkeleton";
import { ProfileSkeleton } from "./ProfileSkeleton";

function PublicLink({ link }: { link: ProfileLink }) {
  return <a className="profile-external-link" href={link.redirect_url} target="_blank" rel="noreferrer">
    <Icon name="link" width={15} height={15} /><span>{link.label}</span>
    <Icon name="external" width={12} height={12} className="external-indicator" />
  </a>;
}

export function ProfilePage() {
  const { user } = useApp();
  const { handle = "" } = useParams();
  return <ProfileContent key={`${handle}:${user?.id ?? "anonymous"}`} username={handle.replace(/^@/, "")} />;
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
  const [tab, setTab] = useState<"posts" | "articles" | "archive">("posts");
  const [refreshKey, setRefreshKey] = useState(0);
  const [pins, setPins] = useState<OriginalFeedItem[]>([]);
  const [pinError, setPinError] = useState("");
  const [pinsLoading, setPinsLoading] = useState(true);
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
  }, [profilePath, user?.id, refreshKey]);

  const refreshActivity = useCallback(() => {
    setRefreshKey((value) => value + 1);
  }, []);

  useEffect(() => {
    window.addEventListener(publicationEvent, refreshActivity);
    window.addEventListener(publicationStateEvent, refreshActivity);
    return () => {
      window.removeEventListener(publicationEvent, refreshActivity);
      window.removeEventListener(publicationStateEvent, refreshActivity);
    };
  }, [refreshActivity]);

  useEffect(() => {
    const controller = new AbortController();
    setPins([]);
    setPinError("");
    setPinsLoading(true);
    api<OriginalFeedItem[]>(`${profilePath}/pins`, { signal: controller.signal, cache: "no-store" })
      .then((items) => { if (!controller.signal.aborted) setPins(items); })
      .catch((reason: unknown) => { if (!controller.signal.aborted) setPinError(errorMessage(reason)); })
      .finally(() => { if (!controller.signal.aborted) setPinsLoading(false); });
    return () => controller.abort();
  }, [profilePath, refreshKey, user?.id]);

  useEffect(() => { setTab("posts"); }, [user?.id]);

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
    : <ProfileSkeleton />;

  const own = user?.id === profile.id;
  const activeTab = tab === "archive" && !own ? "posts" : tab;
  const tabs: ("posts" | "articles" | "archive")[] = own ? ["posts", "articles", "archive"] : ["posts", "articles"];
  const authReturn = { from: location.pathname };
  return <>
    <section className="profile-section motion-fade" aria-label="Profile">
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
        <div className="profile-name-row">
          <h1><HashtagText text={profile.display_name} /></h1>
          {profile.badges.length > 0 && <div className="profile-badges" aria-label="Profile badges">
            {profile.badges.map((badge) => <span className="badge" key={badge.code}
              title={badge.payload.description ?? undefined} style={{ backgroundColor: badge.payload.background_color, color: badge.payload.text_color }}>
              <BadgeIcon badge={badge} />{badge.payload.label}
            </span>)}
          </div>}
        </div>
        <p className="profile-handle">@{profile.username}</p>
        <div className="profile-bio-grid">
          <div>
            {profile.bio && <p className="profile-bio-copy"><HashtagText text={profile.bio} /></p>}
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
      {tabs.map((kind, index) => <button key={kind} type="button" role="tab" id={`tab-${kind}`}
        aria-controls={`panel-${kind}`} aria-selected={activeTab === kind} tabIndex={activeTab === kind ? 0 : -1}
        onClick={() => setTab(kind)} onKeyDown={(event) => {
          if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
          event.preventDefault();
          const nextIndex = event.key === "Home" ? 0 : event.key === "End" ? tabs.length - 1
            : (index + (event.key === "ArrowRight" ? 1 : -1) + tabs.length) % tabs.length;
          const next = tabs[nextIndex];
          setTab(next);
          document.getElementById(`tab-${next}`)?.focus();
        }}>
        {kind === "posts" ? "Posts" : kind === "articles" ? "Articles" : "Archive"}
      </button>)}
    </div>
    <section id={`panel-${activeTab}`} role="tabpanel" aria-labelledby={`tab-${activeTab}`}>
      {activeTab === "archive" && own && user ? <ProfileArchive key={`${user.id}:${refreshKey}`} /> : <>
        {pinError && <p className="notice-error" role="alert">{pinError}{" "}
          <button type="button" className="text-link" onClick={refreshActivity}>Retry pins</button></p>}
        {pinsLoading ? <div className={activeTab === "articles" ? "profile-articles-loading" : ""}>
          <PublicationListSkeleton variant={activeTab === "articles" ? "article" : "post"} />
        </div> : activeTab === "posts"
          ? <ProfileTimeline key={`${profile.username}-${refreshKey}`} username={profile.username}
              pins={pins.filter((item) => item.kind === "micro_post")} onChanged={refreshActivity} />
          : <ProfilePublications key={`${profile.username}-${refreshKey}`} username={profile.username}
              pins={pins.filter((item) => item.kind === "article")} onChanged={refreshActivity} />}
      </>}
    </section>
    <dialog className="design-dialog motion-dialog" ref={linksDialog}>
      <div className="dialog-heading"><h2>All links</h2>
        <button type="button" className="icon-button" aria-label="Close links" onClick={() => linksDialog.current?.close()}><Icon name="close" /></button>
      </div>
      <div className="dialog-body profile-links">{profile.links.map((link) => <PublicLink key={link.id} link={link} />)}</div>
    </dialog>
    <dialog className="design-dialog motion-dialog" ref={networkDialog} onClose={() => setNetworkKind(null)}>
      <div className="dialog-heading"><h2>{networkKind === "followers" ? "Followers" : "Following"}</h2>
        <button type="button" className="icon-button" aria-label="Close profiles" onClick={() => networkDialog.current?.close()}><Icon name="close" /></button>
      </div>
      <div className="dialog-body profile-links">
        <div className="profile-network-results" aria-busy={network.loading}>
          {network.items.map((person) => <div className="discovery-person motion-enter" key={person.id}
            onClick={(event) => { if (event.target instanceof Element && event.target.closest("a")) networkDialog.current?.close(); }}>
            <Link to={`/@${person.username}`}><Avatar src={person.avatars.original} name={person.display_name} size="sm" /></Link>
            <span><strong><HashtagText text={person.display_name} href={`/@${person.username}`} /></strong>
              <small><Link to={`/@${person.username}`}>@{person.username}</Link></small></span>
          </div>)}
        </div>
        {network.loading && !network.error && <PeopleSkeleton count={network.items.length ? 2 : 3} />}
        {network.error && <p className="notice-error" role="alert">{network.error}</p>}
        {!network.loading && !network.error && !network.items.length && <p>No profiles to show.</p>}
        {network.hasMore && <button type="button" className="button-secondary" disabled={network.loading}
          onClick={() => void network.loadMore()}>Load more profiles</button>}
      </div>
    </dialog>
  </>;
}
