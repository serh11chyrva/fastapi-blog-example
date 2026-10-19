import { useApp } from "../AuthProvider";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useState } from "react";
import { api, errorMessage } from "../../shared/api/client";
import { Avatar } from "../../shared/ui/Avatar";
export function Header({ authReady, fullscreen = false }: {
  authReady: boolean;
  fullscreen?: boolean;
}) {
  const { user, setUser } = useApp();
  const navigate = useNavigate();
  const [logoutError, setLogoutError] = useState("");
  async function logout() {
    setLogoutError("");
    try {
      await api("/auth/logout", { method: "POST" });
      setUser(null);
      navigate("/");
    }
    catch (reason) {
      setLogoutError(errorMessage(reason));
    }
  }
  return <>
    <header className="sticky top-0 z-20 border-b border-black/10 bg-white/95 backdrop-blur">
      <div className={`mx-auto flex h-16 items-center justify-between px-5 sm:px-8 ${fullscreen ? "max-w-[1440px]" : "max-w-6xl"}`}>
        <Link to="/" className="flex items-center gap-3">
          <span className="grid h-9 w-9 place-items-center bg-black font-serif text-lg font-bold text-white">c</span>
          <span className="font-serif text-xl font-semibold tracking-tight text-black">commonplace</span>
        </Link>
        <div className="flex items-center gap-3">
          {fullscreen && <Link to="/" className="button-quiet">← Back to site</Link>}
          {user ? <>
            <Link to="/write" className="button-primary hidden sm:inline-flex">Write an article <span aria-hidden>↗</span></Link>
            <Link to={`/@${user.username}`} className="flex items-center gap-2 p-1.5 pr-3 hover:bg-neutral-100">
              <Avatar name={user.display_name} size="sm" />
              <span className="hidden text-sm font-medium text-slate-700 sm:block">
                {user.display_name}
              </span>
            </Link>
            <button className="button-quiet" onClick={logout}>Log out</button>
          </> : authReady ? <>
            <Link className="button-quiet" to="/login">Log in</Link>
            <Link className="button-primary" to="/register">Join the community</Link>
          </> : <span className="text-sm text-slate-400">Loading…</span>}
        </div>
      </div>
    </header>
    {logoutError && <p role="alert" className="notice-error">
      {logoutError}
    </p>}
  </>;
}
export function MobileNav() {
  const { user } = useApp();
  return <nav className="mx-auto flex max-w-6xl gap-2 overflow-x-auto px-4 pt-3 lg:hidden">
    <Link className="pill shrink-0" to="/">Explore</Link>
    <Link className="pill shrink-0" to="/following">Following</Link>
    {user && <>
      <Link className="pill shrink-0" to="/write">Write</Link>
      <Link className="pill shrink-0" to="/saved">Saved</Link>
      <Link className="pill shrink-0" to="/my-articles">My articles</Link>
      <Link className="pill shrink-0" to="/settings/sessions">Sessions</Link>
    </>}
  </nav>;
}
export function Sidebar() {
  const { user } = useApp();
  return <aside className="hidden lg:block">
    <nav className="sticky top-24 space-y-1">


      <SideLink to="/" label="Explore" icon="⌕" />

      <SideLink to="/following" label="Following" icon="↗" />

      {user && <>
        <div className="my-5 border-t border-slate-200" />
        <SideLink to={`/@${user.username}`} label="My profile" icon="◎" />
        <SideLink to="/saved" label="Saved" icon="▱" />
        <SideLink to="/my-articles" label="My articles" icon="▤" />
        <SideLink to="/settings/profile" label="Profile settings" icon="⚙" />
        <SideLink to="/settings/sessions" label="Active sessions" icon="◷" />
      </>}

      <div className="mt-8 rounded-2xl border border-slate-200 bg-white p-4">
        <p className="text-xs font-semibold uppercase tracking-wider text-slate-600">A quieter corner</p>
        <p className="mt-2 text-sm leading-6 text-slate-600">Short notes, considered stories, and people worth reading.</p>
      </div>

    </nav>
  </aside>;
}
export function SideLink({ to, label, icon }: {
  to: string;
  label: string;
  icon: string;
}) {
  const location = useLocation();
  const active = location.pathname === to || (to === "/" && location.pathname === "/");
  return <Link to={to} className={`flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium ${active ? "bg-slate-50 text-slate-700" : "text-slate-600 hover:bg-white hover:text-slate-900"}`}>
    <span className="w-5 text-center text-lg">
      {icon}
    </span>
    {label}
  </Link>;
}
export function RightRail({ authReady }: {
  authReady: boolean;
}) {
  const { user } = useApp();
  return <aside className="hidden lg:block">
    <div className="sticky top-24 space-y-4">
      <div className="rounded-2xl border border-slate-200 bg-white p-5">
        <p className="text-sm font-semibold text-slate-900">A good place to begin</p>
        <p className="mt-2 text-sm leading-6 text-slate-600">Follow a few writers, share a small thought, or take your time with an article.</p>
        {!user && authReady && <Link to="/register" className="mt-4 inline-flex text-sm font-semibold text-slate-700 hover:text-slate-900">Create an account <span className="ml-1">→</span></Link>}
      </div>
      <p className="px-1 text-xs leading-5 text-slate-400">A demonstration project built for thoughtful publishing.</p>
    </div>
  </aside>;
}
