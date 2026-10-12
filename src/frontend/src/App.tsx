import { createContext, useContext, useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";
import { Link, Navigate, Route, Routes, useLocation, useNavigate, useParams } from "react-router-dom";
import { EditorContent, useEditor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import LinkExtension from "@tiptap/extension-link";

type User = { id: string; email: string; username: string; display_name: string };
type Profile = User & { bio: string; links: { label: string; url: string }[]; avatar_url: string | null; badges: { code: string; label: string; description: string | null; assigned_at: string }[]; follower_count: number; following_count: number; is_following: boolean };
type FeedItem = { id: string; kind: "micro_post" | "article"; title?: string | null; text?: string | null; summary?: string | null; author_id: string; author_username: string; author_display_name: string; author_avatar_url: string | null; published_at: string };
type Feed = { items: FeedItem[]; next_cursor: string | null };
type Article = { id: string; kind: "article"; title: string; summary: string; body: Record<string, unknown>; status: "draft" | "published"; author_id: string; author_username: string; author_display_name: string; author_avatar_url: string | null; created_at: string; updated_at: string; published_at: string | null };
type Session = { id: string; created_at: string; last_seen_at: string; expires_at: string; ip_address: string | null; user_agent: string | null; current: boolean };

type AppContextValue = { user: User | null; setUser: (user: User | null) => void };
const AppContext = createContext<AppContextValue>({ user: null, setUser: () => undefined });
const useApp = () => useContext(AppContext);

async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body && !(init.body instanceof FormData)) headers.set("Content-Type", "application/json");
  const response = await fetch(`/api/v1${path}`, { ...init, headers, credentials: "include" });
  if (response.status === 204) return undefined as T;
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.detail || "Something went wrong. Please try again.");
  return payload as T;
}

function Avatar({ src, name, size = "md" }: { src?: string | null; name: string; size?: "sm" | "md" | "lg" }) {
  const dimensions = size === "lg" ? "h-20 w-20 text-2xl" : size === "sm" ? "h-9 w-9 text-xs" : "h-11 w-11 text-sm";
  return src ? <img className={`${dimensions} rounded-full object-cover ring-1 ring-black/5`} src={src} alt={`${name}'s avatar`} /> : <div className={`${dimensions} flex shrink-0 items-center justify-center rounded-full bg-indigo-100 font-semibold text-indigo-700`}>{name.slice(0, 1).toUpperCase()}</div>;
}

function App() {
  const [user, setUser] = useState<User | null>(null);
  const [authReady, setAuthReady] = useState(false);
  useEffect(() => {
    api<User>("/auth/me").then(setUser).catch(() => setUser(null)).finally(() => setAuthReady(true));
  }, []);
  const context = useMemo(() => ({ user, setUser }), [user]);
  return <AppContext.Provider value={context}><div className="min-h-screen bg-[#f6f7f9]"><Header authReady={authReady} /><main className="mx-auto grid w-full max-w-6xl grid-cols-1 gap-7 px-4 py-8 lg:grid-cols-[220px_minmax(0,1fr)_260px]"><Sidebar /><section className="min-w-0"><Routes>
    <Route path="/" element={<FeedPage />} />
    <Route path="/following" element={<FeedPage following />} />
    <Route path="/login" element={<AuthPage />} />
    <Route path="/register" element={<AuthPage />} />
    <Route path="/u/:username" element={<ProfilePage />} />
    <Route path="/articles/:articleId" element={<ArticlePage />} />
    <Route path="/write" element={<ArticleEditorPage />} />
    <Route path="/my-articles" element={<MyArticlesPage />} />
    <Route path="/articles/:articleId/edit" element={<ArticleEditorPage />} />
    <Route path="/settings/profile" element={<ProfileSettingsPage />} />
    <Route path="/settings/sessions" element={<SessionsPage />} />
    <Route path="*" element={<EmptyState title="Page not found" body="The page you are looking for does not exist." />} />
  </Routes></section><RightRail authReady={authReady} /></main></div></AppContext.Provider>;
}

function Header({ authReady }: { authReady: boolean }) {
  const { user, setUser } = useApp();
  const navigate = useNavigate();
  async function logout() {
    try { await api("/auth/logout", { method: "POST" }); } finally { setUser(null); navigate("/"); }
  }
  return <header className="sticky top-0 z-20 border-b border-slate-200/80 bg-white/90 backdrop-blur"><div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4"><Link to="/" className="flex items-center gap-2.5"><span className="grid h-9 w-9 place-items-center rounded-xl bg-indigo-600 text-lg font-bold text-white">c</span><span className="text-lg font-semibold tracking-tight text-slate-900">commonplace</span></Link><div className="flex items-center gap-3">{user ? <><Link to="/write" className="button-primary hidden sm:inline-flex">Write an article <span aria-hidden>↗</span></Link><Link to={`/u/${user.username}`} className="flex items-center gap-2 rounded-full p-1.5 pr-3 hover:bg-slate-100"><Avatar name={user.display_name} size="sm" /><span className="hidden text-sm font-medium text-slate-700 sm:block">{user.display_name}</span></Link><button className="button-quiet" onClick={logout}>Log out</button></> : authReady ? <><Link className="button-quiet" to="/login">Log in</Link><Link className="button-primary" to="/register">Join the community</Link></> : <span className="text-sm text-slate-400">Loading…</span>}</div></div></header>;
}

function Sidebar() {
  const { user } = useApp();
  return <aside className="hidden lg:block"><nav className="sticky top-24 space-y-1">
    <SideLink to="/" label="Explore" icon="⌕" />
    <SideLink to="/following" label="Following" icon="↗" />
    {user && <><div className="my-5 border-t border-slate-200" /><SideLink to={`/u/${user.username}`} label="My profile" icon="◎" /><SideLink to="/my-articles" label="My articles" icon="▤" /><SideLink to="/settings/profile" label="Profile settings" icon="⚙" /><SideLink to="/settings/sessions" label="Active sessions" icon="◷" /></>}
    <div className="mt-8 rounded-2xl border border-slate-200 bg-white p-4"><p className="text-xs font-semibold uppercase tracking-wider text-indigo-600">A quieter corner</p><p className="mt-2 text-sm leading-6 text-slate-600">Short notes, considered stories, and people worth reading.</p></div>
  </nav></aside>;
}

function SideLink({ to, label, icon }: { to: string; label: string; icon: string }) {
  const location = useLocation();
  const active = location.pathname === to || (to === "/" && location.pathname === "/");
  return <Link to={to} className={`flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium ${active ? "bg-indigo-50 text-indigo-700" : "text-slate-600 hover:bg-white hover:text-slate-900"}`}><span className="w-5 text-center text-lg">{icon}</span>{label}</Link>;
}

function RightRail({ authReady }: { authReady: boolean }) {
  const { user } = useApp();
  return <aside className="hidden lg:block"><div className="sticky top-24 space-y-4"><div className="rounded-2xl border border-slate-200 bg-white p-5"><p className="text-sm font-semibold text-slate-900">A good place to begin</p><p className="mt-2 text-sm leading-6 text-slate-600">Follow a few writers, share a small thought, or take your time with an article.</p>{!user && authReady && <Link to="/register" className="mt-4 inline-flex text-sm font-semibold text-indigo-700 hover:text-indigo-900">Create an account <span className="ml-1">→</span></Link>}</div><p className="px-1 text-xs leading-5 text-slate-400">A demonstration project built for thoughtful publishing.</p></div></aside>;
}

function FeedPage({ following = false }: { following?: boolean }) {
  const { user } = useApp();
  const [kind, setKind] = useState("all");
  const [feed, setFeed] = useState<Feed>({ items: [], next_cursor: null });
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState("");
  const [refreshKey, setRefreshKey] = useState(0);
  const feedPath = following ? "/feeds/following" : "/feeds/public";
  useEffect(() => {
    let cancelled = false;
    setBusy(true); setError("");
    api<Feed>(`${feedPath}?kind=${kind}&limit=20`).then((result) => { if (!cancelled) setFeed(result); }).catch((reason: Error) => { if (!cancelled) setError(reason.message); }).finally(() => { if (!cancelled) setBusy(false); });
    return () => { cancelled = true; };
  }, [feedPath, kind, refreshKey]);
  async function loadMore() {
    if (!feed.next_cursor) return;
    try {
      const next = await api<Feed>(`${feedPath}?kind=${kind}&limit=20&cursor=${encodeURIComponent(feed.next_cursor)}`);
      setFeed((current) => ({ items: [...current.items, ...next.items], next_cursor: next.next_cursor }));
    } catch (reason) { setError((reason as Error).message); }
  }
  return <div className="space-y-5"><div className="flex flex-wrap items-end justify-between gap-3"><div><p className="eyebrow">Your reading room</p><h1 className="page-title">{following ? "Following" : "Explore"}</h1><p className="mt-1 text-sm text-slate-500">Fresh notes and stories, in the order they were shared.</p></div><select className="field w-auto py-2" value={kind} onChange={(event) => setKind(event.target.value)} aria-label="Filter publications"><option value="all">Everything</option><option value="micro_post">Short notes</option><option value="article">Articles</option></select></div>
    {!following && user && <PostComposer onPosted={() => setRefreshKey((value) => value + 1)} />}
    {error && <div className="notice-error">{error}{following && !user && <Link className="ml-2 font-semibold underline" to="/login">Log in</Link>}</div>}
    {busy ? <div className="surface p-8 text-center text-sm text-slate-500">Loading the latest posts…</div> : feed.items.length ? <div className="space-y-4">{feed.items.map((item) => <FeedCard key={`${item.kind}-${item.id}`} item={item} onChanged={() => setRefreshKey((value) => value + 1)} />)}{feed.next_cursor && <button className="button-secondary w-full" onClick={loadMore}>Load more</button>}</div> : !error && <EmptyState title={following ? "Your following feed is quiet" : "Nothing has been published yet"} body={following ? "Follow a few profiles and their latest notes will appear here." : "Be the first to share a thought or publish an article."} />}
  </div>;
}

function PostComposer({ onPosted }: { onPosted: () => void }) {
  const [text, setText] = useState(""); const [error, setError] = useState(""); const [saving, setSaving] = useState(false);
  async function submit(event: FormEvent) { event.preventDefault(); setSaving(true); setError(""); try { await api("/posts", { method: "POST", body: JSON.stringify({ text }) }); setText(""); onPosted(); } catch (reason) { setError((reason as Error).message); } finally { setSaving(false); } }
  return <form onSubmit={submit} className="surface p-4 sm:p-5"><div className="flex gap-3"><div className="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-indigo-100 text-sm font-semibold text-indigo-700">✎</div><div className="min-w-0 flex-1"><textarea className="min-h-20 w-full resize-y border-0 bg-transparent p-1 text-[15px] leading-6 outline-none placeholder:text-slate-400" placeholder="What’s on your mind?" maxLength={280} value={text} onChange={(event) => setText(event.target.value)} /><div className="flex flex-wrap items-center justify-between gap-2 border-t border-slate-100 pt-3"><span className="text-xs text-slate-400">{text.length} / 280</span><button className="button-primary" disabled={saving || !text.trim()}>{saving ? "Posting…" : "Share note"}</button></div>{error && <p className="mt-2 text-sm text-rose-600">{error}</p>}</div></div></form>;
}

function FeedCard({ item, onChanged }: { item: FeedItem; onChanged: () => void }) {
  const { user } = useApp();
  const [error, setError] = useState("");
  const isOwner = user?.id === item.author_id;
  async function removePost() {
    if (!confirm("Remove this note from the public feed?")) return;
    try { await api(`/posts/${item.id}`, { method: "DELETE" }); onChanged(); } catch (reason) { setError((reason as Error).message); }
  }
  return <article className="surface p-5 sm:p-6"><div className="flex items-start gap-3"><Link to={`/u/${item.author_username}`}><Avatar src={item.author_avatar_url} name={item.author_display_name} /></Link><div className="min-w-0 flex-1"><div className="flex flex-wrap items-center gap-x-2"><Link to={`/u/${item.author_username}`} className="font-semibold text-slate-900 hover:text-indigo-700">{item.author_display_name}</Link><span className="text-sm text-slate-400">@{item.author_username}</span><span className="text-slate-300">·</span><time className="text-sm text-slate-400">{new Date(item.published_at).toLocaleDateString("en", { month: "short", day: "numeric" })}</time></div>
      {item.kind === "micro_post" ? <p className="mt-2 whitespace-pre-wrap text-[15px] leading-7 text-slate-700">{item.text}</p> : <Link to={`/articles/${item.id}`} className="mt-3 block rounded-xl bg-slate-50 p-4 transition hover:bg-indigo-50/60"><span className="text-xs font-semibold uppercase tracking-wider text-indigo-600">Article</span><h2 className="mt-1 text-lg font-semibold leading-7 text-slate-900">{item.title}</h2>{item.summary && <p className="mt-1 text-sm leading-6 text-slate-600">{item.summary}</p>}<span className="mt-3 inline-flex text-sm font-semibold text-indigo-700">Read article <span className="ml-1">→</span></span></Link>}
      <div className="mt-4 flex items-center justify-between border-t border-slate-100 pt-3"><span className="text-xs text-slate-400">{item.kind === "micro_post" ? "Short note" : "Long-form story"}</span>{isOwner && item.kind === "micro_post" && <button className="text-xs font-medium text-slate-400 hover:text-rose-600" onClick={removePost}>Delete note</button>}</div>{error && <p className="mt-2 text-sm text-rose-600">{error}</p>}
    </div></div></article>;
}

function AuthPage() {
  const location = useLocation(); const navigate = useNavigate(); const { setUser } = useApp();
  const isRegister = location.pathname === "/register";
  const [identifier, setIdentifier] = useState(""); const [email, setEmail] = useState(""); const [username, setUsername] = useState(""); const [displayName, setDisplayName] = useState(""); const [password, setPassword] = useState(""); const [error, setError] = useState(""); const [saving, setSaving] = useState(false);
  async function submit(event: FormEvent) {
    event.preventDefault(); setSaving(true); setError("");
    try {
      const user = isRegister
        ? await api<User>("/auth/register", { method: "POST", body: JSON.stringify({ email, username, display_name: displayName, password }) })
        : await api<User>("/auth/login", { method: "POST", body: JSON.stringify({ identifier, password }) });
      setUser(user); navigate("/");
    } catch (reason) { setError((reason as Error).message); } finally { setSaving(false); }
  }
  return <div className="mx-auto max-w-md"><div className="surface p-6 sm:p-8"><p className="eyebrow">Join commonplace</p><h1 className="mt-2 text-2xl font-semibold tracking-tight text-slate-900">{isRegister ? "Make room for your ideas" : "Welcome back"}</h1><p className="mt-2 text-sm leading-6 text-slate-500">{isRegister ? "Create an account to publish, follow writers, and save a place for longer stories." : "Sign in with your email address or username."}</p>
    <form onSubmit={submit} className="mt-6 space-y-4">{isRegister ? <><label className="form-label">Email<input className="field mt-1.5" type="email" autoComplete="email" required value={email} onChange={(event) => setEmail(event.target.value)} /></label><label className="form-label">Username<input className="field mt-1.5" autoComplete="username" minLength={3} maxLength={24} placeholder="your_handle" required value={username} onChange={(event) => setUsername(event.target.value)} /></label><label className="form-label">Public name<input className="field mt-1.5" autoComplete="name" maxLength={64} required value={displayName} onChange={(event) => setDisplayName(event.target.value)} /></label></> : <label className="form-label">Email or username<input className="field mt-1.5" autoComplete="username" required value={identifier} onChange={(event) => setIdentifier(event.target.value)} /></label>}
      <label className="form-label">Password<input className="field mt-1.5" type="password" autoComplete={isRegister ? "new-password" : "current-password"} minLength={isRegister ? 12 : 1} required value={password} onChange={(event) => setPassword(event.target.value)} /></label>
      {error && <div className="notice-error">{error}</div>}<button className="button-primary w-full justify-center" disabled={saving}>{saving ? "Please wait…" : isRegister ? "Create account" : "Log in"}</button>
    </form><p className="mt-5 text-center text-sm text-slate-500">{isRegister ? "Already have an account?" : "New to commonplace?"} <Link className="font-semibold text-indigo-700 hover:text-indigo-900" to={isRegister ? "/login" : "/register"}>{isRegister ? "Log in" : "Create an account"}</Link></p></div></div>;
}

function ProfilePage() {
  const { username = "" } = useParams(); const { user } = useApp(); const [profile, setProfile] = useState<Profile | null>(null); const [error, setError] = useState("");
  useEffect(() => { api<Profile>(`/users/${encodeURIComponent(username)}`).then(setProfile).catch((reason) => setError((reason as Error).message)); }, [username]);
  async function toggleFollow() {
    if (!profile) return;
    try { await api(`/users/${profile.username}/follow`, { method: profile.is_following ? "DELETE" : "PUT" }); setProfile(await api<Profile>(`/users/${profile.username}`)); }
    catch (reason) { setError((reason as Error).message); }
  }
  if (error) return <EmptyState title="Profile unavailable" body={error} />;
  if (!profile) return <div className="surface p-8 text-center text-sm text-slate-500">Loading profile…</div>;
  const own = user?.id === profile.id;
  return <div className="space-y-4"><section className="surface overflow-hidden"><div className="h-24 bg-gradient-to-r from-indigo-100 via-violet-50 to-amber-50" /><div className="px-5 pb-6 sm:px-7"><div className="-mt-10 flex flex-wrap items-end justify-between gap-4"><Avatar src={profile.avatar_url} name={profile.display_name} size="lg" /><div className="flex gap-2">{own ? <Link to="/settings/profile" className="button-secondary">Edit profile</Link> : user ? <button className={profile.is_following ? "button-secondary" : "button-primary"} onClick={toggleFollow}>{profile.is_following ? "Following" : "Follow"}</button> : <Link className="button-primary" to="/login">Log in to follow</Link>}</div></div><h1 className="mt-4 text-2xl font-semibold text-slate-900">{profile.display_name}</h1><p className="text-sm text-slate-500">@{profile.username}</p>{profile.bio && <p className="mt-4 max-w-2xl whitespace-pre-wrap text-[15px] leading-7 text-slate-700">{profile.bio}</p>}<div className="mt-4 flex gap-5 text-sm"><span><strong className="text-slate-900">{profile.following_count}</strong> <span className="text-slate-500">Following</span></span><span><strong className="text-slate-900">{profile.follower_count}</strong> <span className="text-slate-500">Followers</span></span></div>{profile.links.length > 0 && <div className="mt-4 flex flex-wrap gap-2">{profile.links.map((link) => <a key={link.url} href={link.url} target="_blank" rel="noreferrer" className="pill">↗ {link.label}</a>)}</div>}{profile.badges.length > 0 && <div className="mt-4 flex flex-wrap gap-2">{profile.badges.map((badge) => <span className="badge" key={badge.code}>✦ {badge.label}</span>)}</div>}{error && <p className="mt-3 text-sm text-rose-600">{error}</p>}</div></section><ProfilePublications username={profile.username} /></div>;
}

function ProfilePublications({ username }: { username: string }) {
  const [items, setItems] = useState<FeedItem[]>([]); const [loading, setLoading] = useState(true);
  useEffect(() => { api<FeedItem[]>(`/users/${encodeURIComponent(username)}/publications`).then(setItems).finally(() => setLoading(false)); }, [username]);
  if (loading) return <div className="surface p-6 text-sm text-slate-500">Loading publications…</div>;
  return <div className="space-y-4">{items.length ? items.map((item) => <FeedCard key={item.id} item={item} onChanged={() => setItems((current) => current.filter((entry) => entry.id !== item.id))} />) : <EmptyState title="No public posts yet" body="When this writer publishes something, it will appear here." />}</div>;
}

function MyArticlesPage() {
  const { user } = useApp(); const [articles, setArticles] = useState<Article[]>([]); const [filter, setFilter] = useState("all"); const [error, setError] = useState("");
  useEffect(() => { if (user) api<Article[]>(`/me/articles?status=${filter}`).then(setArticles).catch((reason) => setError((reason as Error).message)); }, [user, filter]);
  if (!user) return <Navigate to="/login" replace />;
  return <div className="space-y-5"><div className="flex flex-wrap items-end justify-between gap-3"><div><p className="eyebrow">Your writing</p><h1 className="page-title">My articles</h1></div><div className="flex gap-2"><select className="field w-auto py-2" value={filter} onChange={(event) => setFilter(event.target.value)} aria-label="Filter articles"><option value="all">All articles</option><option value="draft">Drafts</option><option value="published">Published</option></select><Link className="button-primary" to="/write">Write article</Link></div></div>{error && <div className="notice-error">{error}</div>}{articles.length ? <div className="space-y-3">{articles.map((article) => <article className="surface p-5" key={article.id}><div className="flex flex-wrap items-start justify-between gap-3"><div className="min-w-0"><span className={article.status === "draft" ? "badge bg-amber-50 text-amber-700" : "badge"}>{article.status}</span><Link to={`/articles/${article.id}`} className="mt-2 block text-lg font-semibold text-slate-900 hover:text-indigo-700">{article.title}</Link>{article.summary && <p className="mt-1 text-sm leading-6 text-slate-500">{article.summary}</p>}<p className="mt-2 text-xs text-slate-400">Updated {new Date(article.updated_at).toLocaleDateString()}</p></div><Link className="button-secondary" to={`/articles/${article.id}/edit`}>Edit</Link></div></article>)}</div> : !error && <EmptyState title="No articles yet" body="Your drafts and published articles will appear here." />}</div>;
}

function ArticlePage() {
  const { articleId = "" } = useParams(); const { user } = useApp(); const [article, setArticle] = useState<Article | null>(null); const [error, setError] = useState("");
  useEffect(() => { api<Article>(`/articles/${articleId}`).then(setArticle).catch((reason) => setError((reason as Error).message)); }, [articleId]);
  if (error) return <EmptyState title="Article unavailable" body={error} />;
  if (!article) return <div className="surface p-8 text-center text-sm text-slate-500">Loading article…</div>;
  return <article className="surface p-5 sm:p-9"><Link to={`/u/${article.author_username}`} className="flex items-center gap-3"><Avatar src={article.author_avatar_url} name={article.author_display_name} /><div><p className="font-semibold text-slate-900">{article.author_display_name}</p><p className="text-sm text-slate-500">@{article.author_username} · {article.published_at ? new Date(article.published_at).toLocaleDateString("en", { month: "long", day: "numeric", year: "numeric" }) : "Draft"}</p></div></Link><h1 className="mt-8 text-3xl font-semibold leading-tight tracking-tight text-slate-900 sm:text-4xl">{article.title}</h1>{article.summary && <p className="mt-3 text-lg leading-8 text-slate-500">{article.summary}</p>}{article.status === "draft" && <div className="mt-4 inline-flex rounded-full bg-amber-50 px-3 py-1 text-xs font-semibold text-amber-700">Draft · only visible to you</div>}<div className="mt-8 border-t border-slate-100 pt-6"><TipTapDocument body={article.body} /></div>{user?.id === article.author_id && <div className="mt-8 border-t border-slate-100 pt-5"><Link to={`/articles/${article.id}/edit`} className="button-secondary">Edit article</Link></div>}</article>;
}

function TipTapDocument({ body, editable = false, onChange }: { body: Record<string, unknown>; editable?: boolean; onChange?: (body: Record<string, unknown>) => void }) {
  const editor = useEditor({
    extensions: [StarterKit.configure({ heading: { levels: [1, 2, 3] } }), LinkExtension.configure({ openOnClick: false, HTMLAttributes: { rel: "noopener noreferrer nofollow", target: "_blank" } })],
    content: body,
    editable,
    onUpdate: ({ editor: current }) => onChange?.(current.getJSON() as Record<string, unknown>),
    editorProps: { attributes: { class: `tiptap-content ${editable ? "tiptap-editable" : ""}` } },
  });
  useEffect(() => { if (editor && JSON.stringify(editor.getJSON()) !== JSON.stringify(body)) editor.commands.setContent(body); }, [editor, body]);
  return <EditorContent editor={editor} />;
}

function ArticleEditorPage() {
  const { articleId } = useParams(); const { user } = useApp(); const navigate = useNavigate();
  const [title, setTitle] = useState(""); const [summary, setSummary] = useState(""); const [body, setBody] = useState<Record<string, unknown>>({ type: "doc", content: [{ type: "paragraph" }] });
  const [article, setArticle] = useState<Article | null>(null); const [error, setError] = useState(""); const [saving, setSaving] = useState(false);
  const editor = useEditor({
    extensions: [StarterKit.configure({ heading: { levels: [1, 2, 3] } }), LinkExtension.configure({ openOnClick: false, HTMLAttributes: { rel: "noopener noreferrer nofollow", target: "_blank" } })],
    content: body,
    editable: true,
    onUpdate: ({ editor: current }) => setBody(current.getJSON() as Record<string, unknown>),
    editorProps: { attributes: { class: "tiptap-content tiptap-editable" } },
  });
  useEffect(() => { if (articleId) api<Article>(`/articles/${articleId}`).then((value) => { setArticle(value); setTitle(value.title); setSummary(value.summary); setBody(value.body); }).catch((reason) => setError((reason as Error).message)); }, [articleId]);
  useEffect(() => { if (editor && JSON.stringify(editor.getJSON()) !== JSON.stringify(body)) editor.commands.setContent(body, { emitUpdate: false }); }, [editor, body]);
  if (!user) return <Navigate to="/login" replace />;
  async function save(publish: boolean) {
    if (!title.trim()) { setError("Add a title before saving your article."); return; }
    setSaving(true); setError("");
    try {
      const payload = { title, summary, body };
      let saved = article ? await api<Article>(`/articles/${article.id}`, { method: "PATCH", body: JSON.stringify(payload) }) : await api<Article>("/articles", { method: "POST", body: JSON.stringify(payload) });
      if (publish && saved.status !== "published") saved = await api<Article>(`/articles/${saved.id}/publish`, { method: "POST" });
      setArticle(saved); navigate(`/articles/${saved.id}`);
    } catch (reason) { setError((reason as Error).message); } finally { setSaving(false); }
  }
  return <div className="surface p-5 sm:p-8"><div className="flex flex-wrap items-center justify-between gap-3"><div><p className="eyebrow">Long-form editor</p><h1 className="mt-1 text-2xl font-semibold text-slate-900">{article ? "Edit article" : "New article"}</h1></div><span className="pill">Saved as a draft until published</span></div><label className="form-label mt-7 block">Title<input className="field mt-2 py-3 text-xl font-semibold" maxLength={160} placeholder="Give your story a title" value={title} onChange={(event) => setTitle(event.target.value)} /></label><label className="form-label mt-4 block">Summary<textarea className="field mt-2 min-h-20 resize-y" maxLength={320} placeholder="A short introduction for the feed" value={summary} onChange={(event) => setSummary(event.target.value)} /></label><EditorToolbar editor={editor} /><div className="mt-4 rounded-xl border border-slate-200 bg-white px-4 py-3"><EditorContent editor={editor} /></div>{error && <div className="notice-error mt-4">{error}</div>}<div className="mt-5 flex flex-wrap justify-end gap-2"><button className="button-secondary" disabled={saving} onClick={() => save(false)}>{saving ? "Saving…" : "Save draft"}</button><button className="button-primary" disabled={saving} onClick={() => save(true)}>{saving ? "Saving…" : "Publish article"}</button></div></div>;
}

function EditorToolbar({ editor }: { editor: NonNullable<ReturnType<typeof useEditor>> | null }) {
  const actions: { label: string; run: () => void; active?: boolean }[] = editor ? [
    { label: "B", run: () => editor.chain().focus().toggleBold().run(), active: editor.isActive("bold") },
    { label: "I", run: () => editor.chain().focus().toggleItalic().run(), active: editor.isActive("italic") },
    { label: "H2", run: () => editor.chain().focus().toggleHeading({ level: 2 }).run(), active: editor.isActive("heading", { level: 2 }) },
    { label: "• List", run: () => editor.chain().focus().toggleBulletList().run(), active: editor.isActive("bulletList") },
    { label: "Quote", run: () => editor.chain().focus().toggleBlockquote().run(), active: editor.isActive("blockquote") },
    { label: "Code", run: () => editor.chain().focus().toggleCodeBlock().run(), active: editor.isActive("codeBlock") },
    { label: "Link", run: () => { const current = editor.getAttributes("link").href as string | undefined; const href = window.prompt("Link URL", current || "https://"); if (href === null) return; if (href.trim()) editor.chain().focus().extendMarkRange("link").setLink({ href: href.trim() }).run(); else editor.chain().focus().extendMarkRange("link").unsetLink().run(); }, active: editor.isActive("link") },
  ] : [];
  return <div className="mt-5 flex flex-wrap gap-1 rounded-t-xl border border-slate-200 bg-slate-50 p-2">{actions.map((action) => <button key={action.label} type="button" onClick={action.run} className={`rounded-lg px-3 py-1.5 text-xs font-semibold ${action.active ? "bg-indigo-100 text-indigo-700" : "text-slate-600 hover:bg-white"}`}>{action.label}</button>)}</div>;
}

function ProfileSettingsPage() {
  const { user } = useApp(); const [profile, setProfile] = useState<Profile | null>(null); const [displayName, setDisplayName] = useState(""); const [bio, setBio] = useState(""); const [links, setLinks] = useState<{ label: string; url: string }[]>([]); const [notice, setNotice] = useState(""); const [error, setError] = useState("");
  useEffect(() => { if (user) api<Profile>(`/users/${user.username}`).then((value) => { setProfile(value); setDisplayName(value.display_name); setBio(value.bio); setLinks(value.links); }).catch((reason) => setError((reason as Error).message)); }, [user]);
  if (!user) return <Navigate to="/login" replace />;
  async function save(event: FormEvent) { event.preventDefault(); setNotice(""); setError(""); try { const updated = await api<Profile>("/me/profile", { method: "PATCH", body: JSON.stringify({ display_name: displayName, bio, links }) }); setProfile(updated); setNotice("Your profile has been updated."); } catch (reason) { setError((reason as Error).message); } }
  async function upload(event: FormEvent<HTMLInputElement>) { const file = event.currentTarget.files?.[0]; if (!file) return; const form = new FormData(); form.set("file", file); try { const updated = await api<Profile>("/me/avatar", { method: "PUT", body: form }); setProfile(updated); setNotice("Your avatar has been updated."); } catch (reason) { setError((reason as Error).message); } }
  function updateLink(index: number, key: "label" | "url", value: string) { setLinks((current) => current.map((item, itemIndex) => itemIndex === index ? { ...item, [key]: value } : item)); }
  return <div className="space-y-4"><div><p className="eyebrow">Your account</p><h1 className="page-title">Profile settings</h1></div><form onSubmit={save} className="surface space-y-5 p-5 sm:p-7"><div className="flex items-center gap-4"><Avatar src={profile?.avatar_url} name={displayName || user.display_name} size="lg" /><label className="button-secondary cursor-pointer">Upload avatar<input className="sr-only" type="file" accept="image/jpeg,image/png,image/webp" onChange={upload} /></label><span className="text-xs text-slate-400">JPEG, PNG, or WebP · up to 5 MB</span></div><label className="form-label block">Username<div className="field mt-1.5 bg-slate-50 text-slate-500">@{user.username}</div></label><label className="form-label block">Public name<input className="field mt-1.5" maxLength={64} value={displayName} onChange={(event) => setDisplayName(event.target.value)} /></label><label className="form-label block">Bio<textarea className="field mt-1.5 min-h-24 resize-y" maxLength={280} value={bio} onChange={(event) => setBio(event.target.value)} /></label><div><div className="mb-2 flex items-center justify-between"><span className="form-label">Profile links</span><button type="button" className="text-sm font-semibold text-indigo-700" onClick={() => setLinks((current) => current.length < 8 ? [...current, { label: "", url: "https://" }] : current)}>Add link</button></div><div className="space-y-2">{links.map((link, index) => <div className="grid gap-2 sm:grid-cols-[150px_1fr_auto]" key={index}><input className="field" placeholder="Label" maxLength={32} value={link.label} onChange={(event) => updateLink(index, "label", event.target.value)} /><input className="field" placeholder="https://example.com" value={link.url} onChange={(event) => updateLink(index, "url", event.target.value)} /><button type="button" className="button-quiet" onClick={() => setLinks((current) => current.filter((_, itemIndex) => itemIndex !== index))}>Remove</button></div>)}</div></div>{notice && <div className="notice-success">{notice}</div>}{error && <div className="notice-error">{error}</div>}<button className="button-primary">Save profile</button></form></div>;
}

function SessionsPage() {
  const { user } = useApp(); const [sessions, setSessions] = useState<Session[]>([]); const [error, setError] = useState(""); const [notice, setNotice] = useState("");
  async function load() { try { setSessions(await api<Session[]>("/auth/sessions")); } catch (reason) { setError((reason as Error).message); } }
  useEffect(() => { if (user) void load(); }, [user]);
  if (!user) return <Navigate to="/login" replace />;
  async function revoke(id: string) { try { await api(`/auth/sessions/${id}`, { method: "DELETE" }); setNotice("Session revoked."); await load(); } catch (reason) { setError((reason as Error).message); } }
  async function revokeOthers() { try { await api("/auth/sessions/logout-others", { method: "POST" }); setNotice("All other sessions have been signed out."); await load(); } catch (reason) { setError((reason as Error).message); } }
  return <div className="space-y-4"><div className="flex flex-wrap items-end justify-between gap-3"><div><p className="eyebrow">Account security</p><h1 className="page-title">Active sessions</h1><p className="mt-1 text-sm text-slate-500">Review where your account is signed in.</p></div><button className="button-secondary" onClick={revokeOthers}>Log out other sessions</button></div>{notice && <div className="notice-success">{notice}</div>}{error && <div className="notice-error">{error}</div>}<div className="space-y-3">{sessions.map((session) => <div key={session.id} className="surface flex flex-wrap items-center justify-between gap-4 p-5"><div><div className="flex items-center gap-2"><p className="font-semibold text-slate-900">{session.user_agent || "Unknown device"}</p>{session.current && <span className="badge">Current session</span>}</div><p className="mt-1 text-sm text-slate-500">IP {session.ip_address || "Unavailable"} · Last active {new Date(session.last_seen_at).toLocaleString()}</p><p className="mt-1 text-xs text-slate-400">Expires {new Date(session.expires_at).toLocaleDateString()}</p></div><button className="button-quiet text-rose-600 hover:bg-rose-50" onClick={() => revoke(session.id)}>Revoke</button></div>)}{!sessions.length && !error && <EmptyState title="No active sessions" body="Sign in again to create a session for this device." />}</div></div>;
}

function EmptyState({ title, body }: { title: string; body: string }) { return <div className="surface px-6 py-12 text-center"><div className="mx-auto grid h-12 w-12 place-items-center rounded-2xl bg-indigo-50 text-xl text-indigo-600">✦</div><h2 className="mt-4 font-semibold text-slate-900">{title}</h2><p className="mx-auto mt-1 max-w-sm text-sm leading-6 text-slate-500">{body}</p></div>; }

export default App;
