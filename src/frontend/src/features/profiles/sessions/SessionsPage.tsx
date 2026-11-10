import { usePageTitle } from "../../../app/usePageTitle";
import { useApp } from "../../../app/AuthProvider";
import { Navigate, useNavigate } from "react-router-dom";
import { useEffect, useRef, useState } from "react";
import type { Session } from "../../../shared/api/types";
import { api, errorMessage } from "../../../shared/api/client";
import { EmptyState } from "../../../shared/ui/EmptyState";
export function SessionsPage() {
  usePageTitle("Active sessions");
  const { user, setUser } = useApp();
  const navigate = useNavigate();
  const [sessions, setSessions] = useState<Session[]>([]);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const active = useRef<AbortController | null>(null);
  const [loading, setLoading] = useState(true);
  async function load() {
    active.current?.abort();
    const controller = new AbortController();
    active.current = controller;
    setLoading(true); setError("");
    try {
      const value = await api<Session[]>("/auth/sessions", { signal: controller.signal });
      if (!controller.signal.aborted) setSessions(value);
    } catch (reason) {
      if (!controller.signal.aborted) setError(errorMessage(reason));
    } finally {
      if (!controller.signal.aborted) setLoading(false);
    }
  }
  useEffect(() => {
    if (user)
      void load();
    return () => active.current?.abort();
  }, [user]);
  if (!user)
    return <Navigate to="/login" replace />;
  async function revoke(id: string) {
    try {
      const current = sessions.find((session) => session.id === id)?.current;
      await api(`/auth/sessions/${id}`, { method: "DELETE" });
      if (current) {
        setUser(null);
        navigate("/login");
        return;
      }
      setNotice("Session revoked.");
      await load();
    }
    catch (reason) {
      setError(errorMessage(reason));
    }
  }
  async function revokeOthers() {
    try {
      await api("/auth/sessions/logout-others", { method: "POST" });
      setNotice("All other sessions have been signed out.");
      await load();
    }
    catch (reason) {
      setError(errorMessage(reason));
    }
  }
  return <div className="utility-page space-y-4">
    <div className="flex flex-wrap items-end justify-between gap-3">
      <div>
        <p className="eyebrow">Account security</p>
        <h1 className="page-title">Active sessions</h1>
        <p className="mt-1 text-sm text-slate-500">Review where your account is signed in.</p>
      </div>
      <button className="button-secondary" onClick={revokeOthers}>Log out other sessions</button>
    </div>
    {notice && <div className="notice-success">
      {notice}
    </div>}
    {error && <div className="notice-error">
      {error}
    </div>}
    <div className="space-y-3">
      {sessions.map((session) => <div key={session.id} className="surface flex flex-wrap items-center justify-between gap-4 p-5">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <p className="font-semibold text-slate-900">
              {session.device}
            </p>
            <span className="badge">{{ web: "Web", mobile: "Mobile app", desktop: "Desktop app" }[session.client_type]}</span>
            {session.current && <span className="badge">Current session</span>}
          </div>
          <p className="mt-1 text-sm text-slate-500">{session.location} · Last active {new Date(session.last_seen_at).toLocaleString()}</p>
          <p className="mt-1 text-xs text-slate-400">Expires {new Date(session.expires_at).toLocaleDateString()}</p>
        </div>
        <button className="button-quiet text-slate-700 hover:bg-slate-50" onClick={() => revoke(session.id)}>Revoke</button>
      </div>)}
      {loading && <p role="status">Loading sessions…</p>}
    {!loading && !sessions.length && !error && <EmptyState title="No active sessions" body="Sign in again to create a session for this device." />}
    </div>
  </div>;
}
