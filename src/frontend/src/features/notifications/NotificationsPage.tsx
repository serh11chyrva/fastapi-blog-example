import { usePageTitle } from "../../app/usePageTitle";
import { EmptyState } from "../../shared/ui/EmptyState";
import { Icon } from "../../shared/ui/Icon";
import { InfiniteScroll } from "../../shared/ui/InfiniteScroll";
import { NotificationRow } from "./NotificationRow";
import { useNotificationList } from "./useNotificationList";
import { useNotifications } from "./NotificationsProvider";

export function NotificationsPage() {
  usePageTitle("Notifications");
  const list = useNotificationList();
  const {
    unreadCount, readVersions, queueRead, markAllRead, allBusy, readBusy,
    readError, allError, summaryError, retryReads, refreshSummary,
  } = useNotifications();

  function refresh() {
    window.scrollTo({ top: 0, behavior: "auto" });
    void list.refresh();
    void refreshSummary();
  }

  return <div className="notifications-page">
    <header className="feed-heading notification-heading">
      <div><h1>Notifications</h1><p>Activity and account updates, just for you.</p></div>
      <Icon name="bell" width={22} height={22} />
    </header>
    <div className="notification-toolbar">
      <span className="notification-unread-total" aria-live="polite">{unreadCount} unread</span>
      <div>
        <button type="button" className={list.refreshAvailable ? "button-primary" : "button-quiet"}
          disabled={allBusy || list.loading} onClick={refresh}
          title={list.refreshAvailable ? "Refresh to see the latest notifications" : "Refresh notifications"}>Refresh</button>
        <button type="button" className="button-secondary"
          disabled={allBusy || readBusy || list.loading || !list.loaded || !unreadCount}
          onClick={() => void markAllRead(list.items)}>{allBusy ? "Marking…" : "Mark all as read"}</button>
      </div>
      {list.refreshAvailable && <span className="sr-only" role="status">Refresh to see the latest notifications.</span>}
    </div>
    {summaryError && <p className="notice-error notification-notice" role="alert">
      Could not update the unread count. {summaryError}{" "}
      <button className="underline" type="button" onClick={() => void refreshSummary()}>Retry</button>
    </p>}
    {readError && <p className="notice-error notification-notice" role="alert">
      Could not save viewed notifications. {readError}{" "}
      <button className="underline" type="button" onClick={retryReads}>Retry</button>
    </p>}
    {allError && <p className="notice-error notification-notice" role="alert">{allError}{" "}
      <button className="underline" type="button" disabled={list.loading} onClick={refresh}>Refresh inbox</button>
    </p>}
    <ol className="notification-list" aria-label="Notifications" aria-busy={list.loading}>
      {list.items.map((item) => <NotificationRow key={item.id} item={item}
        isRead={item.is_read || (readVersions.get(item.id) ?? 0) >= item.version} onViewed={queueRead} />)}
    </ol>
    {list.loading && (!list.loaded ? <div className="notification-skeletons" role="status" aria-label="Loading notifications">
      {[0, 1, 2, 3].map((index) => <div className="notification-skeleton" key={index} aria-hidden="true">
        <span className="skeleton notification-skeleton-avatar" /><div><span className="skeleton" /><span className="skeleton" /></div>
      </div>)}
    </div> : <p className="list-status" role="status">Updating notifications…</p>)}
    {list.error && <p className="notice-error notification-notice" role="alert">{list.error}{" "}
      <button type="button" className="underline"
        onClick={list.failedOperation === "more" ? () => void list.loadMore() : refresh}>Retry</button>
    </p>}
    {list.loaded && !list.loading && !list.error && !list.items.length && <EmptyState
      title="You're all caught up" body="Likes, comments, reposts, and account updates will appear here." />}
    <InfiniteScroll hasMore={!!list.cursor} loading={list.loading || allBusy} error={list.error} loadMore={list.loadMore} />
  </div>;
}
