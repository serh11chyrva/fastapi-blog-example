import { useEffect, useRef, useState } from "react";
import { Link, NavLink, useLocation, useNavigate } from "react-router-dom";
import { useApp } from "../AuthProvider";
import { siteName } from "../usePageTitle";
import { api, errorMessage } from "../../shared/api/client";
import type { ArticleFeedItem, Feed, ProfileCard } from "../../shared/api/types";
import { Avatar } from "../../shared/ui/Avatar";
import { Icon } from "../../shared/ui/Icon";
import type { IconName } from "../../shared/ui/Icon";
import { PostComposer } from "../../features/feed/PostComposer";
import { publicationEvent } from "../../features/interactions/events";
import { HashtagText } from "../../shared/text/HashtagText";

export function Brand({ reading = false }: { reading?: boolean }) {
  return <Link to="/" className="site-brand" aria-label={`${siteName} home`}>
    <span className="site-mark"><Icon name={reading ? "pulse" : "sparkle"} width={22} height={22} /></span>
    <span className="site-wordmark">FastAPI<span>Blog Example</span></span>
  </Link>;
}

type NavigationLink = { to: string; label: string; icon: IconName; end?: boolean };

const publicLinks: NavigationLink[] = [
  { to: "/", label: "Explore", icon: "home" },
  { to: "/search", label: "Search", icon: "search" },
  { to: "/following", label: "Following", icon: "following" },
];

export function Navigation({ reading = false }: { reading?: boolean }) {
  const { status, user, setUser } = useApp();
  const location = useLocation();
  const navigate = useNavigate();
  const [collapsed, setCollapsed] = useState(reading);
  const [composeOpen, setComposeOpen] = useState(false);
  const [logoutError, setLogoutError] = useState("");
  const [logoutBusy, setLogoutBusy] = useState(false);
  const dialog = useRef<HTMLDialogElement>(null);
  const accountMenu = useRef<HTMLDetailsElement>(null);
  const profile = user ? `/@${user.username}` : "/login";
  const signIn = { from: location.pathname + location.search + location.hash };
  const privateLinks: NavigationLink[] = [
    { to: profile, label: "Profile", icon: "user" },
    { to: "/my-articles", label: "My articles", icon: "book" },
    { to: "/saved", label: "Bookmarks", icon: "bookmark" },
    { to: "/settings", label: "Settings", icon: "settings", end: false },
  ];

  useEffect(() => {
    function dismissAccountMenu(event: PointerEvent) {
      const menu = accountMenu.current;
      if (menu?.open && event.target instanceof Node && !menu.contains(event.target)) menu.open = false;
    }

    document.addEventListener("pointerdown", dismissAccountMenu);
    return () => document.removeEventListener("pointerdown", dismissAccountMenu);
  }, []);

  async function logout() {
    setLogoutError("");
    setLogoutBusy(true);
    try {
      await api("/auth/logout", { method: "POST" });
      setUser(null);
      navigate("/");
    } catch (reason) {
      setLogoutError(errorMessage(reason));
    } finally {
      setLogoutBusy(false);
    }
  }

  function compose() {
    if (!user) {
      navigate("/login", { state: signIn });
      return;
    }
    dialog.current?.showModal();
    setComposeOpen(true);
  }

  function posted() {
    dialog.current?.close();
    window.dispatchEvent(new Event(publicationEvent));
  }

  const navLinks = user ? [...publicLinks, ...privateLinks] : publicLinks.filter((link) => link.to !== "/following");
  return <aside className={`primary-sidebar ${reading ? "reading-sidebar" : ""}`}>
    <div className="sidebar-brand-row">
      <Brand reading={reading} />
      <button type="button" className="icon-button sidebar-toggle" aria-label="Toggle navigation"
        aria-controls="sidebar-navigation" aria-expanded={!collapsed} onClick={() => setCollapsed((value) => !value)}>
        <Icon name="menu" width={16} height={16} />
      </button>
    </div>
    <div className="sidebar-controls" id="sidebar-navigation" hidden={collapsed}>
      <nav aria-label="Primary navigation" className="sidebar-links">
        {navLinks.map(({ to, label, icon, end = true }) => <NavLink key={to} end={end} to={to}
          className={({ isActive }) => `sidebar-link ${isActive ? "is-active" : ""}`}>
          <Icon name={icon} />{label}
        </NavLink>)}
      </nav>
      <button type="button" className="sidebar-compose" onClick={compose}><Icon name="plus" />New post</button>
      {user && <Link to="/write" className="sidebar-write"><Icon name="write" width={16} height={16} /> Write an article</Link>}
    </div>
    {!collapsed && <div className="sidebar-account">
      {user ? <div className="account-card">
        <div className="account-link">
          <Link to={profile}><Avatar src={user.avatars?.original} name={user.display_name} size="sm" /></Link>
          <span><strong><HashtagText text={user.display_name} href={profile} /></strong>
            <small><Link to={profile}>@{user.username}</Link></small></span>
        </div>
        <details className="account-menu" ref={accountMenu} onBlur={(event) => {
          if (event.relatedTarget && !event.currentTarget.contains(event.relatedTarget)) event.currentTarget.open = false;
        }} onKeyDown={(event) => {
          if (event.key !== "Escape" || !event.currentTarget.open) return;
          event.currentTarget.open = false;
          event.currentTarget.querySelector("summary")?.focus();
        }}>
          <summary className="icon-button" aria-label="Account actions"><Icon name="more" /></summary>
          <div>
            <button type="button" disabled={logoutBusy} onClick={() => void logout()}>Sign out</button>
          </div>
        </details>
      </div> : status === "loading" ? <small role="status">Restoring session…</small> : <>
        <Link to="/login" state={signIn} className="sidebar-link"><Icon name="user" />Sign in</Link>
        <Link to="/register" className="text-link">Create an account</Link>
      </>}
      {logoutError && <p className="notice-error" role="alert">{logoutError}</p>}
    </div>}
    {!reading && <nav className="mobile-bar" aria-label="Mobile navigation">
      <NavLink to="/" end aria-label="Explore"><Icon name="home" width={22} height={22} /></NavLink>
      <NavLink to="/search" aria-label="Search"><Icon name="search" width={22} height={22} /></NavLink>
      {user && <NavLink to="/following" aria-label="Following"><Icon name="following" width={22} height={22} /></NavLink>}
      <button type="button" aria-label="New post" onClick={compose}><Icon name="plus" width={25} height={25} /></button>
      <NavLink to={profile} state={!user ? signIn : undefined} aria-label={user ? "Profile" : "Sign in"}>
        <Icon name="user" width={22} height={22} />
      </NavLink>
      {user && <NavLink to="/saved" aria-label="Bookmarks"><Icon name="bookmark" width={22} height={22} /></NavLink>}
      <details className="mobile-more">
        <summary aria-label="More navigation"><Icon name="menu" width={21} height={21} /></summary>
        <div>
          {user ? <>
            <Link to="/write">Write an article</Link><Link to="/my-articles">My articles</Link>
            <Link to="/settings">Settings</Link>
            <button type="button" disabled={logoutBusy} onClick={() => void logout()}>Sign out</button>
            {logoutError && <p className="notice-error" role="alert">{logoutError}</p>}
          </> : <Link to="/register">Create an account</Link>}
        </div>
      </details>
    </nav>}
    <dialog ref={dialog} className="design-dialog compose-dialog" onClose={() => setComposeOpen(false)}
      onClick={(event) => { if (event.target === dialog.current) dialog.current?.close(); }}>
      <div className="dialog-heading"><h2>New post</h2>
        <button type="button" className="icon-button" onClick={() => dialog.current?.close()} aria-label="Close">
          <Icon name="close" />
        </button>
      </div>
      {composeOpen && user && <PostComposer onPosted={posted} />}
    </dialog>
  </aside>;
}

export function Footer({ reading = false }: { reading?: boolean }) {
  return <footer className="page-footer"><span>© {new Date().getFullYear()} {siteName}</span>
    <nav className="footer-links" aria-label="Footer navigation">
      <a href="https://github.com/serh11chyrva/fastapi-blog-example" target="_blank" rel="noopener noreferrer">GitHub</a>
      <a href="/api/docs" target="_blank" rel="noopener noreferrer">API Docs</a>
      <Link to="/legal">Legal</Link>
      {reading && <a href="#top">Back to top ↑</a>}
    </nav>
  </footer>;
}

export function RightRail() {
  const { user } = useApp();
  const navigate = useNavigate();
  const [handle, setHandle] = useState("");
  const [articles, setArticles] = useState<ArticleFeedItem[]>([]);
  const [writers, setWriters] = useState<ProfileCard[]>([]);
  useEffect(() => {
    const controller = new AbortController();
    api<Feed>("/feeds/public?kind=article&limit=8", { signal: controller.signal }).then((feed) => {
      const entries = feed.items.filter((item): item is ArticleFeedItem => item.kind === "article");
      setArticles(entries.slice(0, 3));
      const authors = new Map(entries.flatMap((item) => item.authors).map((author) => [author.id, author]));
      if (user) authors.delete(user.id);
      setWriters([...authors.values()].slice(0, 3));
    }).catch(() => undefined);
    return () => controller.abort();
  }, [user?.id]);

  return <aside className="discovery-sidebar" aria-label="Discover">
    <form className="discovery-search" onSubmit={(event) => {
      event.preventDefault();
      const value = handle.trim();
      if (value) navigate(`/search?${new URLSearchParams({ q: value, sort: "relevance" })}`);
    }}>
      <Icon name="search" />
      <input type="search" aria-label="Search people and publications" placeholder="Search" value={handle}
        onChange={(event) => setHandle(event.target.value)} maxLength={200} required />
    </form>
    {articles.length > 0 && <details className="discovery-section" open>
      <summary>Latest articles <Icon name="chevron" width={13} height={13} /></summary>
      <ul>{articles.map((article) => <li key={article.id}>
        <div className="discovery-article">
          <small>{article.authors[0] && <HashtagText text={article.authors[0].display_name}
            href={`/@${article.authors[0].username}`} />} · Article</small>
          <strong><HashtagText text={article.title} href={article.share_url ?? `/articles/${article.id}`} /></strong>
          <small>{new Date(article.published_at).toLocaleDateString("en", { month: "long", day: "numeric" })}</small>
        </div>
      </li>)}</ul>
    </details>}
    {writers.length > 0 && <details className="discovery-section" open>
      <summary>Writers <Icon name="chevron" width={13} height={13} /></summary>
      <ul>{writers.map((writer) => <li key={writer.id}><div className="discovery-person">
        <Link to={`/@${writer.username}`}><Avatar src={writer.avatars.original} name={writer.display_name} size="sm" /></Link>
        <span><strong><HashtagText text={writer.display_name} href={`/@${writer.username}`} /></strong>
          <small><Link to={`/@${writer.username}`}>@{writer.username}</Link></small></span>
        <Link to={`/@${writer.username}`} aria-label={`Open @${writer.username}`}><Icon name="right" width={13} height={13} /></Link>
      </div></li>)}</ul>
    </details>}
  </aside>;
}
