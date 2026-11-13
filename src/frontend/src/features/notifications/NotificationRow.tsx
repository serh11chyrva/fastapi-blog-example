import { Fragment, useEffect, useRef } from "react";
import { Link } from "react-router-dom";
import type { NotificationItem, NotificationReceipt, SocialNotification } from "../../shared/api/types";
import { Avatar } from "../../shared/ui/Avatar";
import { Icon } from "../../shared/ui/Icon";
import { exactDateTime, relativeDate } from "../../shared/ui/dates";

function Actors({ item }: { item: SocialNotification }) {
  const remaining = item.event_count - item.actors.length;
  if (!item.actors.length) return <strong>Someone{item.event_count > 1 ? ` and ${item.event_count - 1} others` : ""}</strong>;
  return <>
    {item.actors.map((actor, index) => <Fragment key={actor.id}>
      {index > 0 && (index === item.actors.length - 1 && !remaining ? " and " : ", ")}
      <Link className="notification-actor" to={`/@${actor.username}`}>{actor.display_name}</Link>
    </Fragment>)}
    {remaining > 0 && <> and <strong>{remaining} {remaining === 1 ? "other" : "others"}</strong></>}
  </>;
}

function activity(item: SocialNotification) {
  if (item.kind === "comment") return "commented on your publication";
  if (item.kind === "reply") return "replied to your comment";
  return `${item.kind === "like" ? "liked" : "reposted"} your ${item.target.label}`;
}

export function NotificationRow({ item, isRead, onViewed }: {
  item: NotificationItem;
  isRead: boolean;
  onViewed: (receipt: NotificationReceipt) => void;
}) {
  const row = useRef<HTMLLIElement>(null);
  const { id, version } = item;
  useEffect(() => {
    if (isRead || !row.current || !("IntersectionObserver" in window)) return;
    let visible = false;
    let sent = false;
    let observer: IntersectionObserver | null = null;
    let timer: ReturnType<typeof setTimeout> | null = null;
    function cancel() {
      if (timer !== null) clearTimeout(timer);
      timer = null;
    }
    function observeVisibility() {
      if (!visible || document.visibilityState !== "visible" || !document.hasFocus()) {
        cancel();
        return;
      }
      if (sent || timer !== null) return;
      timer = setTimeout(() => {
        timer = null;
        if (visible && document.visibilityState === "visible" && document.hasFocus()) {
          sent = true;
          onViewed({ id, through_version: version });
        }
      }, 1000);
    }
    function connectObserver() {
      cancel();
      visible = false;
      observer?.disconnect();
      const toolbar = document.querySelector(".notification-toolbar")?.getBoundingClientRect().height ?? 0;
      const navigation = document.querySelector(".mobile-bar")?.getBoundingClientRect().height ?? 0;
      observer = new IntersectionObserver(([entry]) => {
        visible = !!entry?.isIntersecting && entry.intersectionRatio >= 0.5;
        observeVisibility();
      }, { threshold: [0, 0.5], rootMargin: `-${Math.ceil(toolbar)}px 0px -${Math.ceil(navigation)}px 0px` });
      if (row.current) observer.observe(row.current);
    }
    connectObserver();
    document.addEventListener("visibilitychange", observeVisibility);
    window.addEventListener("focus", observeVisibility);
    window.addEventListener("blur", observeVisibility);
    window.addEventListener("resize", connectObserver);
    return () => {
      cancel();
      observer?.disconnect();
      document.removeEventListener("visibilitychange", observeVisibility);
      window.removeEventListener("focus", observeVisibility);
      window.removeEventListener("blur", observeVisibility);
      window.removeEventListener("resize", connectObserver);
    };
  }, [id, version, isRead, onViewed]);

  function opened() { if (!isRead) onViewed({ id, through_version: version }); }
  const icon = item.kind === "login" ? "device" : item.kind === "like" ? "heart"
    : item.kind === "repost" ? "repost" : "comment";
  const actor = item.kind !== "login" ? item.actors[0] : undefined;
  return <li ref={row} className={`notification-row ${isRead ? "" : "is-unread"}`}>
    <div className={`notification-symbol notification-symbol-${item.kind}`} aria-hidden="true">
      {actor ? <Avatar src={actor.avatars.original} name={actor.display_name} /> : <Icon name={icon} width={22} height={22} />}
      {actor && <span className="notification-action-icon"><Icon name={icon} width={12} height={12} /></span>}
    </div>
    <div className="notification-body">
      <p className="notification-description">
        {item.kind === "login" ? <strong>New sign-in to your account</strong> : <><Actors item={item} /> {activity(item)}</>}
      </p>
      {item.kind === "login" ? <>
        <p className="notification-login-details">{item.login.device} · {item.login.location}</p>
        <Link className="notification-destination" to={item.url} onClick={opened}
          onAuxClick={(event) => { if (event.button === 1) opened(); }}>
          Review your sessions <Icon name="right" width={14} height={14} />
        </Link>
      </> : item.target.available && item.target.url ? <Link className="notification-preview" to={item.target.url}
        onClick={opened} onAuxClick={(event) => { if (event.button === 1) opened(); }}>
        {item.target.preview}<Icon name="right" width={14} height={14} />
      </Link> : <p className="notification-unavailable">This publication is currently unavailable.</p>}
      <time className="notification-time" dateTime={item.last_event_at} title={exactDateTime(item.last_event_at)}>
        {relativeDate(item.last_event_at)}
      </time>
    </div>
    {!isRead && <span className="notification-unread-dot" role="img" aria-label="Unread" />}
  </li>;
}
