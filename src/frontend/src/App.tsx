import { createContext, useContext, useEffect, useMemo, useRef, useState } from "react";
import type { FormEvent } from "react";
import { Link, Navigate, Route, Routes, useLocation, useNavigate, useParams } from "react-router-dom";
import { EditorContent, useEditor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import LinkExtension from "@tiptap/extension-link";
import { Node } from "@tiptap/core";
import { api } from "./api";
import { uploadImages } from "./images";

type User = { id: string; email: string; username: string; display_name: string };
type ProfileLinkInput = { version?: 1; id?: string; label: string; url: string };
type ProfileLink = ProfileLinkInput & { version: 1; id: string; platform: string; redirect_url: string };
type ProfileBadge = { version: 2; code: string; payload: { label: string; description: string | null; background_color: string; text_color: string; icon_url: string | null; icon_color: string | null } };
type OwnerBadge = ProfileBadge & { assigned_at: string; preferences: { enabled: boolean }; permissions: { can_disable: boolean } };
type OwnProfile = Omit<Profile, "badges"> & { revision: number; badges: OwnerBadge[] };
type Profile = User & { bio: string; links: ProfileLink[]; avatar_url: string | null; badges: ProfileBadge[]; follower_count: number; following_count: number; is_following: boolean };
type ProfileCard = { id: string; username: string; display_name: string; avatar_url: string | null };
type FeedItem = { id: string; kind: "micro_post" | "article"; share_url: string | null; thumbnail_url?: string | null; images?: string[]; title?: string | null; text?: string | null; summary?: string | null; author_id: string; author_username: string; author_display_name: string; author_avatar_url: string | null; published_at: string };
type Feed = { items: FeedItem[]; next_cursor: string | null };
type MicroPost = { id: string; kind: "micro_post"; share_url: string | null; text: string; images?: string[]; author_id: string; author_username: string; author_display_name: string; author_avatar_url: string | null; created_at: string; updated_at: string };
type Article = { id: string; kind: "article"; share_url: string | null; title: string; summary: string; body: Record<string, unknown>; thumbnail_url: string | null; inline_image_urls?: string[]; status: "draft" | "scheduled" | "published"; author_id: string; author_username: string; author_display_name: string; author_avatar_url: string | null; created_at: string; updated_at: string; scheduled_at: string | null; published_at: string | null };
type Session = { id: string; created_at: string; last_seen_at: string; expires_at: string; ip_address: string | null; user_agent: string | null; current: boolean };

const ArticleImage = Node.create({ name: "image", group: "block", atom: true, draggable: true,
  addAttributes() { return { src: { default: null }, alt: { default: null }, title: { default: null } }; },
  parseHTML() { return [{ tag: "img[src]" }]; },
  renderHTML({ HTMLAttributes }) { return ["img", { ...HTMLAttributes, loading: "lazy" }]; },
});

type AppContextValue = { user: User | null; setUser: (user: User | null) => void };
const AppContext = createContext<AppContextValue>({ user: null, setUser: () => undefined });
const useApp = () => useContext(AppContext);

function BadgeIcon({ badge }: { badge: ProfileBadge }) {
  const { icon_url, icon_color } = badge.payload;
  if (!icon_url) return null;
  return icon_color ? <span className="inline-block h-3.5 w-3.5 shrink-0" aria-hidden="true" style={{ backgroundColor: icon_color, maskImage: `url(${icon_url})`, WebkitMaskImage: `url(${icon_url})`, maskSize: "contain", maskRepeat: "no-repeat", maskPosition: "center" }} /> : <img src={icon_url} className="h-3.5 w-3.5" alt="" aria-hidden="true" />;
}

function Avatar({ src, name, size = "md" }: { src?: string | null; name: string; size?: "sm" | "md" | "lg" }) {
  const dimensions = size === "lg" ? "h-20 w-20 text-2xl" : size === "sm" ? "h-9 w-9 text-xs" : "h-11 w-11 text-sm";
  return src ? <img className={`${dimensions} rounded-full object-cover ring-1 ring-black/5`} src={src} alt={`${name}'s avatar`} /> : <div className={`${dimensions} flex shrink-0 items-center justify-center rounded-full bg-slate-100 font-semibold text-slate-700`}>{name.slice(0, 1).toUpperCase()}</div>;
}

function App() {
  const [user, setUser] = useState<User | null>(null);
  const [authReady, setAuthReady] = useState(false);
  useEffect(() => {
    api<User>("/auth/me").then(setUser).catch(() => setUser(null)).finally(() => setAuthReady(true));
  }, []);
  const context = useMemo(() => ({ user, setUser }), [user]);
  const location = useLocation();
  const fullscreen = /^\/write$/.test(location.pathname) || /^\/articles\/[^/]+(?:\/edit)?$/.test(location.pathname) || /^\/@[^/]+\/[^/]+$/.test(location.pathname);
  return <AppContext.Provider value={context}><div className="min-h-screen bg-white"><Header authReady={authReady} fullscreen={fullscreen} />{fullscreen ? <main className="mx-auto min-h-[calc(100vh-4rem)] w-full max-w-[1440px] px-5 py-10 sm:px-8"><Routes>
    <Route path="/articles/:articleId" element={<ArticlePage />} />
    <Route path="/@:handle/:shareSlug" element={<SharedPublicationPage />} />
    <Route path="/write" element={<ArticleEditorPage />} />
    <Route path="/articles/:articleId/edit" element={<ArticleEditorPage />} />
  </Routes></main> : <><MobileNav /><main className="mx-auto grid w-full max-w-6xl grid-cols-1 gap-7 px-4 py-8 lg:grid-cols-[210px_minmax(0,1fr)_240px]"><Sidebar /><section className="min-w-0"><Routes>
    <Route path="/" element={<FeedPage />} />
    <Route path="/following" element={<FeedPage following />} />
    <Route path="/login" element={<AuthPage />} />
    <Route path="/register" element={<AuthPage />} />
    <Route path="/:handle" element={<ProfilePage />} />
    <Route path="/:handle/:shareSlug" element={<SharedPublicationPage />} />
    <Route path="/my-articles" element={<MyArticlesPage />} />
    <Route path="/settings/profile" element={<ProfileSettingsPage />} />
    <Route path="/settings/sessions" element={<SessionsPage />} />
    <Route path="*" element={<EmptyState title="Page not found" body="The page you are looking for does not exist." />} />
  </Routes></section><RightRail authReady={authReady} /></main></>}</div></AppContext.Provider>;
}

function Header({ authReady, fullscreen = false }: { authReady: boolean; fullscreen?: boolean }) {
  const { user, setUser } = useApp();
  const navigate = useNavigate();
  async function logout() {
    try { await api("/auth/logout", { method: "POST" }); } finally { setUser(null); navigate("/"); }
  }
  return <header className="sticky top-0 z-20 border-b border-black/10 bg-white/95 backdrop-blur"><div className={`mx-auto flex h-16 items-center justify-between px-5 sm:px-8 ${fullscreen ? "max-w-[1440px]" : "max-w-6xl"}`}><Link to="/" className="flex items-center gap-3"><span className="grid h-9 w-9 place-items-center bg-black font-serif text-lg font-bold text-white">c</span><span className="font-serif text-xl font-semibold tracking-tight text-black">commonplace</span></Link><div className="flex items-center gap-3">{fullscreen && <Link to="/" className="button-quiet">← Back to site</Link>}{user ? <><Link to="/write" className="button-primary hidden sm:inline-flex">Write an article <span aria-hidden>↗</span></Link><Link to={`/@${user.username}`} className="flex items-center gap-2 p-1.5 pr-3 hover:bg-neutral-100"><Avatar name={user.display_name} size="sm" /><span className="hidden text-sm font-medium text-slate-700 sm:block">{user.display_name}</span></Link><button className="button-quiet" onClick={logout}>Log out</button></> : authReady ? <><Link className="button-quiet" to="/login">Log in</Link><Link className="button-primary" to="/register">Join the community</Link></> : <span className="text-sm text-slate-400">Loading…</span>}</div></div></header>;
}

function MobileNav() {
  const { user } = useApp();
  return <nav className="mx-auto flex max-w-6xl gap-2 overflow-x-auto px-4 pt-3 lg:hidden"><Link className="pill shrink-0" to="/">Explore</Link><Link className="pill shrink-0" to="/following">Following</Link>{user && <><Link className="pill shrink-0" to="/write">Write</Link><Link className="pill shrink-0" to="/my-articles">My articles</Link><Link className="pill shrink-0" to="/settings/sessions">Sessions</Link></>}</nav>;
}

function Sidebar() {
  const { user } = useApp();
  return <aside className="hidden lg:block"><nav className="sticky top-24 space-y-1">
    <SideLink to="/" label="Explore" icon="⌕" />
    <SideLink to="/following" label="Following" icon="↗" />
    {user && <><div className="my-5 border-t border-slate-200" /><SideLink to={`/@${user.username}`} label="My profile" icon="◎" /><SideLink to="/my-articles" label="My articles" icon="▤" /><SideLink to="/settings/profile" label="Profile settings" icon="⚙" /><SideLink to="/settings/sessions" label="Active sessions" icon="◷" /></>}
    <div className="mt-8 rounded-2xl border border-slate-200 bg-white p-4"><p className="text-xs font-semibold uppercase tracking-wider text-slate-600">A quieter corner</p><p className="mt-2 text-sm leading-6 text-slate-600">Short notes, considered stories, and people worth reading.</p></div>
  </nav></aside>;
}

function SideLink({ to, label, icon }: { to: string; label: string; icon: string }) {
  const location = useLocation();
  const active = location.pathname === to || (to === "/" && location.pathname === "/");
  return <Link to={to} className={`flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium ${active ? "bg-slate-50 text-slate-700" : "text-slate-600 hover:bg-white hover:text-slate-900"}`}><span className="w-5 text-center text-lg">{icon}</span>{label}</Link>;
}

function RightRail({ authReady }: { authReady: boolean }) {
  const { user } = useApp();
  return <aside className="hidden lg:block"><div className="sticky top-24 space-y-4"><div className="rounded-2xl border border-slate-200 bg-white p-5"><p className="text-sm font-semibold text-slate-900">A good place to begin</p><p className="mt-2 text-sm leading-6 text-slate-600">Follow a few writers, share a small thought, or take your time with an article.</p>{!user && authReady && <Link to="/register" className="mt-4 inline-flex text-sm font-semibold text-slate-700 hover:text-slate-900">Create an account <span className="ml-1">→</span></Link>}</div><p className="px-1 text-xs leading-5 text-slate-400">A demonstration project built for thoughtful publishing.</p></div></aside>;
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
  const [text, setText] = useState(""); const [images, setImages] = useState<File[]>([]); const [error, setError] = useState(""); const [saving, setSaving] = useState(false);
  const [pendingPost, setPendingPost] = useState<MicroPost | null>(null);
  async function submit(event: FormEvent) { event.preventDefault(); setSaving(true); setError(""); try { const post = await api<MicroPost>(pendingPost ? `/posts/${pendingPost.id}` : "/posts", { method: pendingPost ? "PATCH" : "POST", body: JSON.stringify({ text }) }); setPendingPost(post); if (images.length) await uploadImages<MicroPost>(`/posts/${post.id}/images`, images); setPendingPost(null); setText(""); setImages([]); onPosted(); } catch (reason) { setError((reason as Error).message); onPosted(); } finally { setSaving(false); } }
  function chooseFiles(files: FileList | null) { if (!files) return; const selected = Array.from(files); if (selected.length > 5) { setError("Choose up to five images."); return; } setImages(selected); }
  return <form onSubmit={submit} className="surface p-4 sm:p-5"><div className="flex gap-3"><div className="grid h-10 w-10 shrink-0 place-items-center bg-neutral-100 font-serif text-lg font-semibold text-black">✎</div><div className="min-w-0 flex-1"><textarea className="min-h-20 w-full resize-y border-0 bg-transparent p-1 text-[15px] leading-6 outline-none placeholder:text-slate-400" placeholder="What’s on your mind?" maxLength={280} value={text} onChange={(event) => setText(event.target.value)} />{images.length > 0 && <p className="mb-3 text-xs text-neutral-500">{images.map((file) => file.name).join(" · ")}</p>}<div className="flex flex-wrap items-center justify-between gap-2 border-t border-slate-100 pt-3"><div className="flex items-center gap-3"><span className="text-xs text-slate-400">{text.length} / 280</span><label className="cursor-pointer text-xs font-semibold text-neutral-600 hover:text-black">Add images<input className="sr-only" type="file" disabled={saving} accept="image/jpeg,image/png,image/webp" multiple onChange={(event) => chooseFiles(event.target.files)} /></label><span className="text-xs text-neutral-400">Up to 5</span></div><button className="button-primary" disabled={saving || !text.trim()}>{saving ? "Posting…" : "Share note"}</button></div>{error && <p className="mt-2 text-sm text-slate-700">{error}</p>}</div></div></form>;
}

function FeedCard({ item, onChanged }: { item: FeedItem; onChanged: () => void }) {
  const { user } = useApp();
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);
  const [editing, setEditing] = useState(false);
  const [editText, setEditText] = useState(item.text || "");
  const isOwner = user?.id === item.author_id;
  async function share() {
    if (!item.share_url) return;
    await navigator.clipboard.writeText(new URL(item.share_url, window.location.origin).toString());
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1800);
  }
  async function removePost() {
    if (!confirm("Remove this note from the public feed?")) return;
    try { await api(`/posts/${item.id}`, { method: "DELETE" }); onChanged(); } catch (reason) { setError((reason as Error).message); }
  }
  async function savePostEdit() {
    try { await api(`/posts/${item.id}`, { method: "PATCH", body: JSON.stringify({ text: editText }) }); setEditing(false); onChanged(); }
    catch (reason) { setError((reason as Error).message); }
  }
  return <article className="surface p-5 sm:p-6"><div className="flex items-start gap-3"><Link to={`/@${item.author_username}`}><Avatar src={item.author_avatar_url} name={item.author_display_name} /></Link><div className="min-w-0 flex-1"><div className="flex flex-wrap items-center gap-x-2"><Link to={`/@${item.author_username}`} className="font-semibold text-slate-900 hover:text-slate-600">{item.author_display_name}</Link><span className="text-sm text-slate-400">@{item.author_username}</span><span className="text-slate-300">·</span><time className="text-sm text-slate-400">{new Date(item.published_at).toLocaleDateString("en", { month: "short", day: "numeric" })}</time></div>
      {item.kind === "micro_post" ? editing ? <div className="mt-3 space-y-2"><textarea className="field min-h-24 resize-y" maxLength={280} value={editText} onChange={(event) => setEditText(event.target.value)} /><div className="flex justify-end gap-2"><button className="button-quiet" onClick={() => setEditing(false)}>Cancel</button><button className="button-secondary" onClick={() => void savePostEdit()}>Save note</button></div></div> : <><p className="mt-2 whitespace-pre-wrap text-[15px] leading-7 text-slate-800">{item.text}</p>{!!item.images?.length && <div className={`post-gallery mt-4 ${item.images.length === 1 ? "single" : ""}`}>{item.images.map((src, index) => <img src={src} key={src} alt={`Post image ${index + 1}`} loading="lazy" />)}</div>}</> : <Link to={item.share_url || `/articles/${item.id}`} className="mt-3 block overflow-hidden border border-neutral-200 transition hover:border-black">{item.thumbnail_url && <img className="max-h-64 w-full object-cover" src={item.thumbnail_url} alt="Article thumbnail" />}<div className="p-4"><span className="text-xs font-semibold uppercase tracking-wider text-slate-500">Article</span><h2 className="editorial-title mt-1 text-xl font-semibold leading-7 text-black">{item.title}</h2>{item.summary && <p className="mt-1 text-sm leading-6 text-slate-600">{item.summary}</p>}<span className="mt-3 inline-flex text-sm font-semibold text-slate-700">Read article <span className="ml-1">→</span></span></div></Link>}
      <div className="mt-4 flex items-center justify-between border-t border-slate-100 pt-3"><span className="text-xs text-slate-400">{item.kind === "micro_post" ? "Short note" : "Long-form story"}</span><div className="flex items-center gap-2"><button className="text-xs font-medium text-slate-500 hover:text-slate-900" onClick={() => void share()}>{copied ? "Link copied" : "Share"}</button>{isOwner && item.kind === "micro_post" && <><button className="text-xs font-medium text-slate-500 hover:text-slate-900" onClick={() => setEditing((value) => !value)}>Edit note</button><button className="text-xs font-medium text-slate-400 hover:text-slate-700" onClick={removePost}>Delete note</button></>}</div></div>{error && <p className="mt-2 text-sm text-slate-700">{error}</p>}
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
    </form><p className="mt-5 text-center text-sm text-slate-500">{isRegister ? "Already have an account?" : "New to commonplace?"} <Link className="font-semibold text-slate-700 hover:text-slate-900" to={isRegister ? "/login" : "/register"}>{isRegister ? "Log in" : "Create an account"}</Link></p></div></div>;
}

function ProfilePage() {
  const { handle = "" } = useParams(); const username = handle.replace(/^@/, ""); const { user } = useApp(); const [profile, setProfile] = useState<OwnProfile | null>(null); const [error, setError] = useState("");
  const [tab, setTab] = useState<"micro_post" | "article">("micro_post"); const [refreshKey, setRefreshKey] = useState(0);
  const [network, setNetwork] = useState<ProfileCard[] | null>(null);
  const [networkKind, setNetworkKind] = useState<"followers" | "following">("followers");
  useEffect(() => { api<Profile>(`/users/${encodeURIComponent(username)}`).then(setProfile).catch((reason) => setError((reason as Error).message)); }, [username]);
  async function toggleFollow() {
    if (!profile) return;
    try { await api(`/users/${profile.username}/follow`, { method: profile.is_following ? "DELETE" : "PUT" }); setProfile(await api<Profile>(`/users/${profile.username}`)); }
    catch (reason) { setError((reason as Error).message); }
  }
  async function showNetwork(kind: "followers" | "following") {
    setNetworkKind(kind);
    try { setNetwork(await api<ProfileCard[]>(`/users/${profile?.username}/${kind}`)); }
    catch (reason) { setError((reason as Error).message); }
  }
  if (error) return <EmptyState title="Profile unavailable" body={error} />;
  if (!profile) return <div className="surface p-8 text-center text-sm text-slate-500">Loading profile…</div>;
  const own = user?.id === profile.id;
  return <div className="space-y-5"><section className="surface overflow-hidden"><div className="h-20 bg-neutral-100" /><div className="px-5 pb-6 sm:px-7"><div className="-mt-10 flex flex-wrap items-end justify-between gap-4"><Avatar src={profile.avatar_url} name={profile.display_name} size="lg" /><div className="flex gap-2">{own ? <Link to="/settings/profile" className="button-secondary">Edit profile</Link> : user ? <button className={profile.is_following ? "button-secondary" : "button-primary"} onClick={toggleFollow}>{profile.is_following ? "Following" : "Follow"}</button> : <Link className="button-primary" to="/login">Log in to follow</Link>}</div></div><h1 className="editorial-title mt-4 text-3xl font-semibold text-black">{profile.display_name}</h1><p className="text-sm text-slate-500">@{profile.username}</p>{profile.bio && <p className="mt-4 max-w-2xl whitespace-pre-wrap text-[15px] leading-7 text-slate-700">{profile.bio}</p>}<div className="mt-4 flex gap-5 text-sm"><button onClick={() => void showNetwork("following")}><strong className="text-slate-900">{profile.following_count}</strong> <span className="text-slate-500">Following</span></button><button onClick={() => void showNetwork("followers")}><strong className="text-slate-900">{profile.follower_count}</strong> <span className="text-slate-500">Followers</span></button></div>{network && <div className="mt-4 border-t border-slate-100 pt-4"><p className="mb-3 text-sm font-semibold text-slate-700">{networkKind === "followers" ? "Followers" : "Following"}</p><div className="flex flex-wrap gap-3">{network.map((person) => <Link className="flex items-center gap-2 border border-slate-200 px-3 py-2" key={person.id} to={`/@${person.username}`}><Avatar src={person.avatar_url} name={person.display_name} size="sm" /><span className="text-sm">{person.display_name}</span></Link>)}</div></div>}{profile.links.length > 0 && <div className="mt-4 flex flex-wrap gap-2">{profile.links.map((link) => <a key={link.id} href={link.redirect_url} data-platform={link.platform} target="_blank" rel="noreferrer" className="pill">↗ {link.label}</a>)}</div>}{profile.badges.length > 0 && <div className="mt-4 flex flex-wrap gap-2">{profile.badges.map((badge) => <span className="badge gap-1.5" key={badge.code} title={badge.payload.description || undefined} style={{ backgroundColor: badge.payload.background_color, color: badge.payload.text_color }}><BadgeIcon badge={badge} /> {badge.payload.label}</span>)}</div>}{error && <p className="mt-3 text-sm text-slate-700">{error}</p>}</div></section><div className="flex gap-7 border-b border-neutral-200"><button className={`profile-tab ${tab === "micro_post" ? "active" : ""}`} onClick={() => setTab("micro_post")}>Posts</button><button className={`profile-tab ${tab === "article" ? "active" : ""}`} onClick={() => setTab("article")}>Articles</button></div>{tab === "micro_post" && own && <PostComposer onPosted={() => setRefreshKey((value) => value + 1)} />}<ProfilePublications key={`${profile.username}-${tab}-${refreshKey}`} username={profile.username} kind={tab} onChanged={() => setRefreshKey((value) => value + 1)} /></div>;
}

function ProfilePublications({ username, kind, onChanged }: { username: string; kind: "micro_post" | "article"; onChanged: () => void }) {
  const [items, setItems] = useState<FeedItem[]>([]); const [loading, setLoading] = useState(true);
  useEffect(() => { api<FeedItem[]>(`/users/${encodeURIComponent(username)}/publications?kind=${kind}`).then(setItems).finally(() => setLoading(false)); }, [username, kind]);
  if (loading) return <div className="surface p-6 text-sm text-slate-500">Loading publications…</div>;
  return <div className={kind === "article" ? "grid gap-4 sm:grid-cols-2" : "space-y-4"}>{items.length ? items.map((item) => kind === "article" ? <Link className="article-card" key={item.id} to={item.share_url || `/articles/${item.id}`}><div className={`article-card-image ${item.thumbnail_url ? "has-image" : ""}`}>{item.thumbnail_url && <img src={item.thumbnail_url} alt="" loading="lazy" />}</div><div className="p-4"><p className="eyebrow">Article</p><h2 className="editorial-title mt-1 text-xl font-semibold leading-7 text-black">{item.title}</h2>{item.summary && <p className="mt-2 line-clamp-3 text-sm leading-6 text-neutral-600">{item.summary}</p>}<time className="mt-4 block text-xs text-neutral-400">{new Date(item.published_at).toLocaleDateString()}</time></div></Link> : <FeedCard key={item.id} item={item} onChanged={onChanged} />) : <EmptyState title={kind === "article" ? "No articles yet" : "No posts yet"} body="When this writer publishes something, it will appear here." />}</div>;
}

function MyArticlesPage() {
  const { user } = useApp(); const [articles, setArticles] = useState<Article[]>([]); const [filter, setFilter] = useState("all"); const [error, setError] = useState("");
  useEffect(() => { if (user) api<Article[]>(`/me/articles?status=${filter}`).then(setArticles).catch((reason) => setError((reason as Error).message)); }, [user, filter]);
  if (!user) return <Navigate to="/login" replace />;
  return <div className="space-y-5"><div className="flex flex-wrap items-end justify-between gap-3"><div><p className="eyebrow">Your writing</p><h1 className="page-title">My articles</h1></div><div className="flex gap-2"><select className="field w-auto py-2" value={filter} onChange={(event) => setFilter(event.target.value)} aria-label="Filter articles"><option value="all">All articles</option><option value="draft">Drafts</option><option value="scheduled">Scheduled</option><option value="published">Published</option></select><Link className="button-primary" to="/write">Write article</Link></div></div>{error && <div className="notice-error">{error}</div>}{articles.length ? <div className="space-y-3">{articles.map((article) => <article className="surface p-5" key={article.id}><div className="flex flex-wrap items-start justify-between gap-3"><div className="min-w-0"><span className="badge">{article.status}</span>{article.thumbnail_url && <img className="mt-3 max-h-36 rounded-lg object-cover" src={article.thumbnail_url} alt="Article thumbnail" />}<Link to={article.status === "published" ? article.share_url || `/articles/${article.id}` : `/articles/${article.id}`} className="mt-2 block text-lg font-semibold text-slate-900 hover:text-slate-600">{article.title}</Link>{article.summary && <p className="mt-1 text-sm leading-6 text-slate-500">{article.summary}</p>}{article.scheduled_at && <p className="mt-2 text-xs text-slate-500">Scheduled for {new Date(article.scheduled_at).toLocaleString()}</p>}<p className="mt-2 text-xs text-slate-400">Updated {new Date(article.updated_at).toLocaleDateString()}</p></div><Link className="button-secondary" to={`/articles/${article.id}/edit`}>Edit</Link></div></article>)}</div> : !error && <EmptyState title="No articles yet" body="Your drafts and published articles will appear here." />}</div>;
}

function ArticlePage() {
  const { articleId = "" } = useParams(); const { user } = useApp(); const [article, setArticle] = useState<Article | null>(null); const [error, setError] = useState("");
  useEffect(() => { api<Article>(`/articles/${articleId}`).then(setArticle).catch((reason) => setError((reason as Error).message)); }, [articleId]);
  if (error) return <EmptyState title="Article unavailable" body={error} />;
  if (!article) return <div className="surface p-8 text-center text-sm text-slate-500">Loading article…</div>;
  return <ArticlePresentation article={article} owner={user?.id === article.author_id} />;
}

function SharedPublicationPage() {
  const { handle = "", shareSlug = "" } = useParams();
  const username = handle.replace(/^@/, "");
  const [publication, setPublication] = useState<Article | MicroPost | null>(null);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);
  useEffect(() => { api<Article | MicroPost>(`/publications/${encodeURIComponent(username)}/${encodeURIComponent(shareSlug)}`).then(setPublication).catch((reason) => setError((reason as Error).message)); }, [username, shareSlug]);
  if (error) return <EmptyState title="Publication unavailable" body={error} />;
  if (!publication) return <div className="surface p-8 text-center text-sm text-slate-500">Loading publication…</div>;
  if (publication.kind === "article") return <ArticlePresentation article={publication} owner={false} />;
  return <article className="surface mx-auto max-w-2xl p-6 sm:p-9"><Link className="flex items-center gap-3" to={`/@${publication.author_username}`}><Avatar src={publication.author_avatar_url} name={publication.author_display_name} /><div><p className="font-semibold text-slate-900">{publication.author_display_name}</p><p className="text-sm text-slate-500">@{publication.author_username}</p></div></Link><p className="mt-8 whitespace-pre-wrap text-xl leading-9 text-slate-800">{publication.text}</p>{!!publication.images?.length && <div className={`post-gallery mt-4 ${publication.images.length === 1 ? "single" : ""}`}>{publication.images.map((src, index) => <img src={src} key={src} alt={`Post image ${index + 1}`} />)}</div>}<div className="mt-6 flex items-center justify-between border-t border-slate-100 pt-4"><time className="text-sm text-slate-400">{new Date(publication.created_at).toLocaleString()}</time><button className="button-secondary" onClick={() => { const url = publication.share_url && new URL(publication.share_url, window.location.origin).toString(); if (url) void navigator.clipboard.writeText(url).then(() => { setCopied(true); window.setTimeout(() => setCopied(false), 1800); }); }}>{copied ? "Link copied" : "Share"}</button></div></article>;
}

function ArticlePresentation({ article, owner }: { article: Article; owner: boolean }) {
  const [copied, setCopied] = useState(false);
  async function share() {
    if (!article.share_url) return;
    await navigator.clipboard.writeText(new URL(article.share_url, window.location.origin).toString());
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1800);
  }
  return <article className="mx-auto max-w-[760px] pb-20"><div className="mb-8 flex items-center justify-between border-b border-neutral-200 pb-5"><Link to={`/@${article.author_username}`} className="flex items-center gap-3"><Avatar src={article.author_avatar_url} name={article.author_display_name} /><div><p className="font-semibold text-black">{article.author_display_name}</p><p className="text-sm text-neutral-500">@{article.author_username} · {article.published_at ? new Date(article.published_at).toLocaleDateString("en", { month: "long", day: "numeric", year: "numeric" }) : article.status}</p></div></Link><div className="flex gap-2">{owner && <Link to={`/articles/${article.id}/edit`} className="button-secondary">Edit</Link>}{article.status === "published" && <button className="button-secondary" onClick={() => void share()}>{copied ? "Link copied" : "Share"}</button>}</div></div><h1 className="editorial-title text-4xl font-semibold leading-[1.08] tracking-tight text-black sm:text-6xl">{article.title}</h1>{article.thumbnail_url ? <img className="mt-8 max-h-[34rem] w-full object-cover" src={article.thumbnail_url} alt={`Thumbnail for ${article.title}`} /> : <div className="mt-8 h-28 w-full bg-neutral-50" aria-label="No article cover image" />}{article.summary && <p className="editorial-title mt-8 text-xl leading-8 text-neutral-600 sm:text-2xl sm:leading-9">{article.summary}</p>}{article.status !== "published" && <div className="mt-5 inline-flex border border-neutral-300 px-3 py-1 text-xs font-semibold text-neutral-600">{article.status === "scheduled" ? `Scheduled · ${article.scheduled_at ? new Date(article.scheduled_at).toLocaleString() : ""}` : "Draft · only visible to you"}</div>}<div className="article-body mt-10"><TipTapDocument body={article.body} /></div></article>;
}

function TipTapDocument({ body, editable = false, onChange }: { body: Record<string, unknown>; editable?: boolean; onChange?: (body: Record<string, unknown>) => void }) {
  const editor = useEditor({
    extensions: [StarterKit.configure({ heading: { levels: [1, 2, 3] } }), ArticleImage, LinkExtension.configure({ openOnClick: false, HTMLAttributes: { rel: "noopener noreferrer nofollow", target: "_blank" } })],
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
  const [thumbnailFile, setThumbnailFile] = useState<File | null>(null); const [thumbnailPreview, setThumbnailPreview] = useState("");
  const [publishAt, setPublishAt] = useState("");
  const imageInput = useRef<HTMLInputElement>(null);
  const editor = useEditor({
    extensions: [StarterKit.configure({ heading: { levels: [1, 2, 3] } }), ArticleImage, LinkExtension.configure({ openOnClick: false, HTMLAttributes: { rel: "noopener noreferrer nofollow", target: "_blank" } })],
    content: body,
    editable: true,
    onUpdate: ({ editor: current }) => setBody(current.getJSON() as Record<string, unknown>),
    editorProps: { attributes: { class: "tiptap-content tiptap-editable" } },
  });
  useEffect(() => { if (articleId) api<Article>(`/articles/${articleId}`).then((value) => { setArticle(value); setTitle(value.title); setSummary(value.summary); setBody(value.body); if (value.scheduled_at) { const local = new Date(value.scheduled_at); local.setMinutes(local.getMinutes() - local.getTimezoneOffset()); setPublishAt(local.toISOString().slice(0, 16)); } }).catch((reason) => setError((reason as Error).message)); }, [articleId]);
  useEffect(() => {
    if (!thumbnailFile) { setThumbnailPreview(""); return; }
    const url = URL.createObjectURL(thumbnailFile);
    setThumbnailPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [thumbnailFile]);
  useEffect(() => { if (editor && JSON.stringify(editor.getJSON()) !== JSON.stringify(body)) editor.commands.setContent(body, { emitUpdate: false }); }, [editor, body]);
  if (!user) return <Navigate to="/login" replace />;
  async function persist(): Promise<Article> {
    if (!title.trim()) throw new Error("Add a title before saving your article.");
    const payload = { title, summary, body };
    let saved = article ? await api<Article>(`/articles/${article.id}`, { method: "PATCH", body: JSON.stringify(payload) }) : await api<Article>("/articles", { method: "POST", body: JSON.stringify(payload) });
    setArticle(saved);
    if (thumbnailFile) {
      saved = await uploadImages<Article>(`/articles/${saved.id}/cover`, [thumbnailFile]);
      setThumbnailFile(null);
    }
    setArticle(saved);
    return saved;
  }
  async function uploadInlineImage(file: File) {
    if (saving) return;
    setSaving(true); setError("");
    try {
      const saved = article || await persist();
      const uploaded = await uploadImages<{ url: string; alt_text: string }>(`/articles/${saved.id}/images`, [file]);
      editor?.chain().focus().insertContent({ type: "image", attrs: { src: uploaded.url, alt: uploaded.alt_text } }).run();
    } catch (reason) { setError((reason as Error).message); } finally { setSaving(false); }
  }
  async function runAction(action: "draft" | "delete" | "publish" | "schedule") {
    if (action === "delete" && (!article || !confirm("Delete this article? This removes it from public pages."))) return;
    if (action === "schedule" && !publishAt) { setError("Choose a date and time for publication."); return; }
    setSaving(true); setError("");
    try {
      if (action === "delete" && article) {
        await api(`/articles/${article.id}`, { method: "DELETE" });
        navigate("/my-articles");
        return;
      }
      let saved = await persist();
      if (action === "draft" && saved.status !== "draft") saved = await api<Article>(`/articles/${saved.id}/draft`, { method: "POST" });
      if (action === "publish") saved = await api<Article>(`/articles/${saved.id}/publish`, { method: "POST" });
      if (action === "schedule") saved = await api<Article>(`/articles/${saved.id}/schedule`, { method: "POST", body: JSON.stringify({ publish_at: new Date(publishAt).toISOString() }) });
      setArticle(saved);
      navigate(saved.status === "published" ? saved.share_url || `/articles/${saved.id}` : `/articles/${saved.id}`);
    } catch (reason) { setError((reason as Error).message); } finally { setSaving(false); }
  }
  const preview = thumbnailPreview || article?.thumbnail_url;
  return <div className="mx-auto max-w-4xl space-y-5"><div className="flex flex-wrap items-end justify-between gap-3"><div><p className="eyebrow">Writing room</p><p className="editorial-title text-sm font-semibold text-neutral-500">{article ? "Edit article" : "New article"}</p></div><span className="pill">{article?.status || "draft"}</span></div><div className="surface p-5 sm:p-9"><h1 className="editorial-title"><input aria-label="Article title" className="w-full border-0 bg-transparent p-0 text-4xl font-semibold leading-tight tracking-tight text-black outline-none placeholder:text-neutral-300 sm:text-5xl" maxLength={160} placeholder="Give your story a title" value={title} onChange={(event) => setTitle(event.target.value)} /></h1><div className="mt-7 rounded border border-dashed border-neutral-300 p-3">{preview ? <img className="mb-3 h-48 w-full object-cover sm:h-64" src={preview} alt="Article thumbnail preview" /> : <div className="mb-3 flex h-24 w-full items-center justify-center bg-neutral-50 text-xs text-neutral-400">Wide cover image · optional</div>}<div className="flex flex-wrap items-center justify-between gap-3"><div><p className="text-sm font-semibold text-black">Cover image</p><p className="mt-1 text-xs text-neutral-500">JPEG, PNG, or WebP · up to 10 MB</p></div><label className="button-secondary cursor-pointer">{preview ? "Replace image" : "Choose image"}<input className="sr-only" type="file" accept="image/jpeg,image/png,image/webp" onChange={(event) => setThumbnailFile(event.target.files?.[0] || null)} disabled={saving} /></label></div></div><label className="form-label mt-6 block">Summary<textarea className="field mt-2 min-h-20 resize-y" maxLength={320} placeholder="A short introduction for readers" value={summary} onChange={(event) => setSummary(event.target.value)} /></label><div className="mt-8"><p className="form-label mb-2 block">Story</p>{saving && <p role="status" className="mb-2 text-sm text-neutral-500">Saving your article and images…</p>}<EditorToolbar editor={editor} onAddImage={() => { if (!saving) imageInput.current?.click(); }} /><input ref={imageInput} disabled={saving} className="hidden" type="file" accept="image/jpeg,image/png,image/webp" onChange={(event) => { const file = event.target.files?.[0]; if (file) void uploadInlineImage(file); event.currentTarget.value = ""; }} /><div className="rounded-b border border-t-0 border-neutral-200 bg-white px-4 py-4"><EditorContent editor={editor} /></div></div></div><section className="surface p-5 sm:p-7"><div className="flex flex-wrap items-center justify-between gap-3"><div><p className="text-sm font-semibold text-black">Publishing</p><p className="mt-1 text-sm text-neutral-500">Save a draft, publish now, or schedule a time.</p></div><span className="badge">{article?.status || "draft"}</span></div>{article?.scheduled_at && <p className="mt-4 border border-neutral-200 px-3 py-2 text-sm text-neutral-600">Scheduled for {new Date(article.scheduled_at).toLocaleString()}</p>}<div className="mt-5 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between"><label className="form-label">Publish after<input className="field mt-1.5 sm:w-64" type="datetime-local" value={publishAt} onChange={(event) => setPublishAt(event.target.value)} /></label><div className="flex flex-wrap gap-2"><button className="button-secondary" disabled={saving} onClick={() => void runAction("draft")}>Draft</button>{article && <button className="button-secondary" disabled={saving} onClick={() => void runAction("delete")}>Delete</button>}<button className="button-secondary" disabled={saving} onClick={() => void runAction("schedule")}>Publish after…</button><button className="button-primary" disabled={saving} onClick={() => void runAction("publish")}>{saving ? "Saving…" : "Publish now"}</button></div></div>{error && <div className="notice-error mt-4">{error}</div>}</section></div>;
}

function EditorToolbar({ editor, onAddImage }: { editor: NonNullable<ReturnType<typeof useEditor>> | null; onAddImage?: () => void }) {
  const actions: { label: string; run: () => void; active?: boolean }[] = editor ? [
    { label: "B", run: () => editor.chain().focus().toggleBold().run(), active: editor.isActive("bold") },
    { label: "I", run: () => editor.chain().focus().toggleItalic().run(), active: editor.isActive("italic") },
    { label: "S", run: () => editor.chain().focus().toggleStrike().run(), active: editor.isActive("strike") },
    { label: "H1", run: () => editor.chain().focus().toggleHeading({ level: 1 }).run(), active: editor.isActive("heading", { level: 1 }) },
    { label: "H2", run: () => editor.chain().focus().toggleHeading({ level: 2 }).run(), active: editor.isActive("heading", { level: 2 }) },
    { label: "H3", run: () => editor.chain().focus().toggleHeading({ level: 3 }).run(), active: editor.isActive("heading", { level: 3 }) },
    { label: "• List", run: () => editor.chain().focus().toggleBulletList().run(), active: editor.isActive("bulletList") },
    { label: "1. List", run: () => editor.chain().focus().toggleOrderedList().run(), active: editor.isActive("orderedList") },
    { label: "Quote", run: () => editor.chain().focus().toggleBlockquote().run(), active: editor.isActive("blockquote") },
    { label: "Code", run: () => editor.chain().focus().toggleCodeBlock().run(), active: editor.isActive("codeBlock") },
    { label: "Link", run: () => { const current = editor.getAttributes("link").href as string | undefined; const href = window.prompt("Link URL", current || "https://"); if (href === null) return; if (href.trim()) editor.chain().focus().extendMarkRange("link").setLink({ href: href.trim() }).run(); else editor.chain().focus().extendMarkRange("link").unsetLink().run(); }, active: editor.isActive("link") },
    ...(onAddImage ? [{ label: "Image", run: onAddImage }] : []),
  ] : [];
  return <div className="mt-5 flex flex-wrap gap-1 rounded-t-xl border border-slate-200 bg-slate-50 p-2">{actions.map((action) => <button key={action.label} type="button" onClick={action.run} className={`rounded-lg px-3 py-1.5 text-xs font-semibold ${action.active ? "bg-slate-100 text-slate-700" : "text-slate-600 hover:bg-white"}`}>{action.label}</button>)}</div>;
}

function ProfileSettingsPage() {
  const { user } = useApp(); const [profile, setProfile] = useState<OwnProfile | null>(null); const [displayName, setDisplayName] = useState(""); const [bio, setBio] = useState(""); const [links, setLinks] = useState<ProfileLinkInput[]>([]); const [notice, setNotice] = useState(""); const [error, setError] = useState("");
  const [uploading, setUploading] = useState(false);
  const [saving, setSaving] = useState(false);
  async function loadProfile() {
    const value = await api<OwnProfile>("/me/profile");
    setProfile(value); setDisplayName(value.display_name); setBio(value.bio);
    setLinks(value.links.map(({ version, id, label, url }) => ({ version, id, label, url })));
  }
  useEffect(() => { if (user) void loadProfile().catch((reason) => setError((reason as Error).message)); }, [user]);
  if (!user) return <Navigate to="/login" replace />;
  async function save(event: FormEvent) { event.preventDefault(); if (!profile || saving || uploading) return; setSaving(true); setNotice(""); setError(""); try { const updated = await api<OwnProfile>("/me/profile", { method: "PATCH", body: JSON.stringify({ revision: profile.revision, display_name: displayName, bio, links }) }); setProfile(updated); setDisplayName(updated.display_name); setBio(updated.bio); setLinks(updated.links.map(({ version, id, label, url }) => ({ version, id, label, url }))); setNotice("Your profile has been updated."); } catch (reason) { setError((reason as Error).message); } finally { setSaving(false); } }
  async function toggleBadge(badge: OwnerBadge) {
    if (!profile || saving || uploading) return;
    setSaving(true); setError(""); setNotice("");
    try {
      const updated = await api<OwnProfile>(`/me/badges/${badge.code}`, { method: "PATCH", body: JSON.stringify({ revision: profile.revision, enabled: !badge.preferences.enabled }) });
      setProfile(updated); setNotice("Badge visibility has been updated.");
    } catch (reason) { setError((reason as Error).message); }
    finally { setSaving(false); }
  }
  async function upload(event: FormEvent<HTMLInputElement>) {
    const file = event.currentTarget.files?.[0];
    event.currentTarget.value = "";
    if (!file || uploading || saving || !profile) return;
    setUploading(true); setError(""); setNotice("");
    try {
      const updated = await uploadImages<OwnProfile>("/me/avatar", [file]);
      setProfile(updated.revision === profile.revision + 1 ? updated : { ...profile, avatar_url: updated.avatar_url });
      setNotice("Your avatar has been updated.");
    } catch (reason) { setError((reason as Error).message); }
    finally { setUploading(false); }
  }
  function updateLink(index: number, key: "label" | "url", value: string) { setLinks((current) => current.map((item, itemIndex) => itemIndex === index ? { ...item, [key]: value } : item)); }
  return <div className="space-y-4"><div><p className="eyebrow">Your account</p><h1 className="page-title">Profile settings</h1></div><form onSubmit={save} className="surface space-y-5 p-5 sm:p-7"><fieldset className="contents" disabled={saving || uploading}><div className="flex items-center gap-4"><Avatar src={profile?.avatar_url} name={displayName || user.display_name} size="lg" /><label className="button-secondary cursor-pointer">{uploading ? "Uploading…" : "Upload avatar"}<input className="sr-only" type="file" accept="image/jpeg,image/png,image/webp" onChange={upload} disabled={uploading} /></label><span className="text-xs text-slate-400">JPEG, PNG, or WebP · up to 5 MB</span></div><label className="form-label block">Username<div className="field mt-1.5 bg-slate-50 text-slate-500">@{user.username}</div></label><label className="form-label block">Public name<input className="field mt-1.5" maxLength={64} value={displayName} onChange={(event) => setDisplayName(event.target.value)} /></label><label className="form-label block">Bio<textarea className="field mt-1.5 min-h-24 resize-y" maxLength={280} value={bio} onChange={(event) => setBio(event.target.value)} /></label><div><div className="mb-2 flex items-center justify-between"><span className="form-label">Profile links</span><button type="button" className="text-sm font-semibold text-slate-700" onClick={() => setLinks((current) => current.length < 8 ? [...current, { label: "", url: "https://" }] : current)}>Add link</button></div><div className="space-y-2">{links.map((link, index) => <div className="grid gap-2 sm:grid-cols-[150px_1fr_auto]" key={index}><input className="field" placeholder="Label" maxLength={32} value={link.label} onChange={(event) => updateLink(index, "label", event.target.value)} /><input className="field" placeholder="https://example.com" value={link.url} onChange={(event) => updateLink(index, "url", event.target.value)} /><button type="button" className="button-quiet" onClick={() => setLinks((current) => current.filter((_, itemIndex) => itemIndex !== index))}>Remove</button></div>)}</div></div>{profile && profile.badges.length > 0 && <div><p className="form-label mb-2">Badge visibility</p><div className="space-y-2">{profile.badges.map((badge) => <label className="flex items-center gap-3 text-sm" key={badge.code}><input type="checkbox" checked={badge.preferences.enabled} disabled={!badge.permissions.can_disable && badge.preferences.enabled} onChange={() => void toggleBadge(badge)} /><BadgeIcon badge={badge} /><span>{badge.payload.label}</span>{!badge.permissions.can_disable && <span className="text-xs text-slate-500">Required badge</span>}</label>)}</div></div>}{notice && <div className="notice-success">{notice}</div>}{error && <div className="notice-error">{error}<button type="button" className="ml-2 underline" onClick={() => { void loadProfile().then(() => setError("")).catch((reason) => setError((reason as Error).message)); }}>Reload saved profile (discard form edits)</button></div>}<button className="button-primary" disabled={saving || uploading || !profile}>{saving ? "Saving…" : "Save profile"}</button></fieldset></form></div>;
}

function SessionsPage() {
  const { user, setUser } = useApp(); const navigate = useNavigate(); const [sessions, setSessions] = useState<Session[]>([]); const [error, setError] = useState(""); const [notice, setNotice] = useState("");
  async function load() { try { setSessions(await api<Session[]>("/auth/sessions")); } catch (reason) { setError((reason as Error).message); } }
  useEffect(() => { if (user) void load(); }, [user]);
  if (!user) return <Navigate to="/login" replace />;
  async function revoke(id: string) { try { const current = sessions.find((session) => session.id === id)?.current; await api(`/auth/sessions/${id}`, { method: "DELETE" }); if (current) { setUser(null); navigate("/login"); return; } setNotice("Session revoked."); await load(); } catch (reason) { setError((reason as Error).message); } }
  async function revokeOthers() { try { await api("/auth/sessions/logout-others", { method: "POST" }); setNotice("All other sessions have been signed out."); await load(); } catch (reason) { setError((reason as Error).message); } }
  return <div className="space-y-4"><div className="flex flex-wrap items-end justify-between gap-3"><div><p className="eyebrow">Account security</p><h1 className="page-title">Active sessions</h1><p className="mt-1 text-sm text-slate-500">Review where your account is signed in.</p></div><button className="button-secondary" onClick={revokeOthers}>Log out other sessions</button></div>{notice && <div className="notice-success">{notice}</div>}{error && <div className="notice-error">{error}</div>}<div className="space-y-3">{sessions.map((session) => <div key={session.id} className="surface flex flex-wrap items-center justify-between gap-4 p-5"><div><div className="flex items-center gap-2"><p className="font-semibold text-slate-900">{session.user_agent || "Unknown device"}</p>{session.current && <span className="badge">Current session</span>}</div><p className="mt-1 text-sm text-slate-500">IP {session.ip_address || "Unavailable"} · Last active {new Date(session.last_seen_at).toLocaleString()}</p><p className="mt-1 text-xs text-slate-400">Expires {new Date(session.expires_at).toLocaleDateString()}</p></div><button className="button-quiet text-slate-700 hover:bg-slate-50" onClick={() => revoke(session.id)}>Revoke</button></div>)}{!sessions.length && !error && <EmptyState title="No active sessions" body="Sign in again to create a session for this device." />}</div></div>;
}

function EmptyState({ title, body }: { title: string; body: string }) { return <div className="surface px-6 py-12 text-center"><div className="mx-auto grid h-12 w-12 place-items-center rounded-2xl bg-slate-50 text-xl text-slate-600">✦</div><h2 className="mt-4 font-semibold text-slate-900">{title}</h2><p className="mx-auto mt-1 max-w-sm text-sm leading-6 text-slate-500">{body}</p></div>; }

export default App;
