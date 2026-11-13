import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";
import { useApp } from "../../app/AuthProvider";
import { api, errorMessage } from "../../shared/api/client";
import type { NotificationItem, NotificationReceipt, NotificationSummary } from "../../shared/api/types";

type NotificationContextValue = {
  unreadCount: number;
  summaryError: string;
  readError: string;
  allError: string;
  readBusy: boolean;
  allBusy: boolean;
  readVersions: ReadonlyMap<string, number>;
  queueRead: (receipt: NotificationReceipt) => void;
  retryReads: () => void;
  markAllRead: (snapshot: NotificationItem[]) => Promise<boolean>;
  refreshSummary: () => Promise<void>;
  subscribeToPoll: (listener: () => void) => () => void;
};

const NotificationContext = createContext<NotificationContextValue | null>(null);

export function NotificationsProvider({ children }: { children: ReactNode }) {
  const { user } = useApp();
  return <NotificationSession key={user?.id ?? "anonymous"} accountId={user?.id ?? null}>
    {children}
  </NotificationSession>;
}

function NotificationSession({ accountId, children }: { accountId: string | null; children: ReactNode }) {
  const [unreadCount, setUnreadCount] = useState(0);
  const [summaryError, setSummaryError] = useState("");
  const [readError, setReadError] = useState("");
  const [allError, setAllError] = useState("");
  const [readBusy, setReadBusy] = useState(false);
  const [allBusy, setAllBusy] = useState(false);
  const [readVersions, setReadVersions] = useState<ReadonlyMap<string, number>>(new Map());
  const scope = useRef<AbortController | null>(null);
  const pending = useRef(new Map<string, number>());
  const acknowledged = useRef(new Map<string, number>());
  const inFlight = useRef<Map<string, number> | null>(null);
  const allRunning = useRef(false);
  const blocked = useRef(false);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const flush = useRef<() => Promise<void>>(async () => undefined);
  const listeners = useRef(new Set<() => void>());
  const summaryGeneration = useRef(0);
  const summaryRequest = useRef<Promise<void> | null>(null);

  const refreshSummary = useCallback((force = false): Promise<void> => {
    const session = scope.current;
    if (!accountId || !session || session.signal.aborted) return Promise.resolve();
    if (summaryRequest.current && !force) return summaryRequest.current;
    const generation = ++summaryGeneration.current;
    const request = api<NotificationSummary>("/me/notifications/summary", { signal: session.signal })
      .then((summary) => {
        if (session.signal.aborted || generation !== summaryGeneration.current) return;
        setUnreadCount(summary.unread_count);
        setSummaryError("");
      })
      .catch((reason: unknown) => {
        if (!session.signal.aborted && generation === summaryGeneration.current)
          setSummaryError(errorMessage(reason));
      })
      .finally(() => {
        if (summaryRequest.current === request) summaryRequest.current = null;
      });
    summaryRequest.current = request;
    return request;
  }, [accountId]);

  const scheduleFlush = useCallback(() => {
    if (timer.current !== null || blocked.current || allRunning.current || inFlight.current) return;
    timer.current = setTimeout(() => {
      timer.current = null;
      void flush.current();
    }, 200);
  }, []);

  const acknowledge = useCallback((receipts: Map<string, number>) => {
    for (const [id, version] of receipts)
      acknowledged.current.set(id, Math.max(acknowledged.current.get(id) ?? 0, version));
    setReadVersions(new Map(acknowledged.current));
  }, []);

  flush.current = async () => {
    const session = scope.current;
    if (!accountId || !session || session.signal.aborted || blocked.current || allRunning.current || inFlight.current)
      return;
    for (const [id, version] of pending.current)
      if (version <= (acknowledged.current.get(id) ?? 0)) pending.current.delete(id);
    const batch = new Map([...pending.current].slice(0, 50));
    if (!batch.size) return;
    for (const id of batch.keys()) pending.current.delete(id);
    inFlight.current = batch;
    setReadBusy(true);
    try {
      await api("/me/notifications/read", {
        method: "PUT", signal: session.signal,
        body: JSON.stringify({ items: [...batch].map(([id, through_version]) => ({ id, through_version })) }),
      });
      if (session.signal.aborted) return;
      acknowledge(batch);
      setReadError("");
      void refreshSummary(true);
    } catch (reason) {
      if (session.signal.aborted) return;
      for (const [id, version] of batch)
        pending.current.set(id, Math.max(pending.current.get(id) ?? 0, version));
      blocked.current = true;
      setReadError(errorMessage(reason));
      void refreshSummary(true);
    } finally {
      if (!session.signal.aborted) {
        inFlight.current = null;
        setReadBusy(false);
        if (pending.current.size) scheduleFlush();
      }
    }
  };

  const queueRead = useCallback(({ id, through_version }: NotificationReceipt) => {
    if (!accountId || scope.current?.signal.aborted) return;
    const known = Math.max(
      acknowledged.current.get(id) ?? 0, pending.current.get(id) ?? 0, inFlight.current?.get(id) ?? 0,
    );
    if (through_version <= known) return;
    pending.current.set(id, through_version);
    scheduleFlush();
  }, [accountId, scheduleFlush]);

  const retryReads = useCallback(() => {
    void refreshSummary(true).then(() => {
      if (scope.current?.signal.aborted) return;
      blocked.current = false;
      setReadError("");
      scheduleFlush();
    });
  }, [refreshSummary, scheduleFlush]);

  const markAllRead = useCallback(async (snapshot: NotificationItem[]) => {
    const session = scope.current;
    if (!accountId || !session || session.signal.aborted || allRunning.current || inFlight.current) return false;
    allRunning.current = true;
    setAllBusy(true);
    setAllError("");
    if (timer.current !== null) {
      clearTimeout(timer.current);
      timer.current = null;
    }
    const versions = new Map(snapshot.map((item) => [item.id, item.version]));
    try {
      await api("/me/notifications/read-all", { method: "PUT", signal: session.signal });
      if (session.signal.aborted) return false;
      acknowledge(versions);
      blocked.current = false;
      setReadError("");
      await refreshSummary(true);
      return true;
    } catch (reason) {
      if (!session.signal.aborted) {
        setAllError(`${errorMessage(reason)} Refresh the inbox before trying again.`);
        void refreshSummary(true);
      }
      return false;
    } finally {
      if (!session.signal.aborted) {
        allRunning.current = false;
        setAllBusy(false);
        if (pending.current.size) scheduleFlush();
      }
    }
  }, [accountId, acknowledge, refreshSummary, scheduleFlush]);

  const subscribeToPoll = useCallback((listener: () => void) => {
    listeners.current.add(listener);
    return () => { listeners.current.delete(listener); };
  }, []);

  useEffect(() => {
    const session = new AbortController();
    scope.current = session;
    let lastPoll = 0;
    function poll() {
      if (!accountId || allRunning.current || document.visibilityState !== "visible" || !navigator.onLine) return;
      if (Date.now() - lastPoll < 1000) return;
      lastPoll = Date.now();
      void refreshSummary();
      for (const listener of listeners.current) listener();
    }
    poll();
    const interval = setInterval(poll, 30_000);
    document.addEventListener("visibilitychange", poll);
    window.addEventListener("focus", poll);
    window.addEventListener("online", poll);
    return () => {
      session.abort();
      clearInterval(interval);
      if (timer.current !== null) clearTimeout(timer.current);
      timer.current = null;
      summaryGeneration.current++;
      summaryRequest.current = null;
      inFlight.current = null;
      document.removeEventListener("visibilitychange", poll);
      window.removeEventListener("focus", poll);
      window.removeEventListener("online", poll);
    };
  }, [accountId, refreshSummary]);

  const value = useMemo(() => ({
    unreadCount, summaryError, readError, allError, readBusy, allBusy, readVersions,
    queueRead, retryReads, markAllRead, refreshSummary, subscribeToPoll,
  }), [unreadCount, summaryError, readError, allError, readBusy, allBusy, readVersions,
    queueRead, retryReads, markAllRead, refreshSummary, subscribeToPoll]);
  return <NotificationContext.Provider value={value}>{children}</NotificationContext.Provider>;
}

export function useNotifications() {
  const context = useContext(NotificationContext);
  if (!context) throw new Error("Notification context is unavailable");
  return context;
}

export function NotificationBadge() {
  const { unreadCount, summaryError } = useNotifications();
  if (!unreadCount && !summaryError) return null;
  return <span className="notification-badge" title={summaryError || `${unreadCount} unread notifications`}
    aria-label={summaryError ? "Notification count is temporarily unavailable" : `${unreadCount} unread notifications`}>
    {unreadCount ? unreadCount > 99 ? "99+" : unreadCount : "!"}
  </span>;
}
