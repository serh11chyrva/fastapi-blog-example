import { Link, useLocation, useNavigate } from "react-router-dom";
import { siteName, usePageTitle } from "../../app/usePageTitle";
import { useApp } from "../../app/AuthProvider";
import { useState } from "react";
import { Icon } from "../../shared/ui/Icon";
import type { FormEvent } from "react";
import { api, errorMessage } from "../../shared/api/client";
import type { User } from "../../shared/api/types";
export function AuthPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const { setUser } = useApp();
  const isRegister = location.pathname === "/register";
  usePageTitle(isRegister ? "Create an account" : "Sign in");
  const [identifier, setIdentifier] = useState("");
  const [email, setEmail] = useState("");
  const [username, setUsername] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (saving) return;
    setSaving(true);
    setError("");
    try {
      const user = isRegister
        ? await api<User>("/auth/register", { method: "POST", body: JSON.stringify({ email, username, display_name: displayName, password }) })
        : await api<User>("/auth/login", { method: "POST", body: JSON.stringify({ identifier, password }) });
      setUser(user);
      const from: unknown = location.state?.from;
      const target = typeof from === "string" && from.startsWith("/") && !from.startsWith("//")
        && !/[\\\u0000-\u0020]/.test(from) ? from : "/";
      navigate(target, { replace: true });
    }
    catch (reason) {
      setError(errorMessage(reason));
    }
    finally {
      setSaving(false);
    }
  }
  return <main className="auth-page">
    <section className="auth-panel" aria-labelledby="auth-title">
      <Link to="/" className="auth-brand" aria-label={`${siteName} home`}>{siteName}<span>.</span></Link>
      <h1 id="auth-title">{isRegister ? "Create an account" : "Welcome back"}</h1>
      <form onSubmit={submit}>
        {isRegister ? <>
          <div className="auth-field"><label htmlFor="auth-email">Email</label>
            <input id="auth-email" type="email" autoComplete="email" placeholder="you@example.com"
              required value={email} onChange={(event) => setEmail(event.target.value)} /></div>
          <div className="auth-field"><label htmlFor="auth-user">Username</label>
            <input id="auth-user" autoComplete="username" minLength={3} maxLength={24} placeholder="your_handle"
              required value={username} onChange={(event) => setUsername(event.target.value)} /></div>
          <div className="auth-field"><label htmlFor="auth-name">Public name</label>
            <input id="auth-name" autoComplete="name" maxLength={64} required
              value={displayName} onChange={(event) => setDisplayName(event.target.value)} /></div>
        </> : <div className="auth-field"><label htmlFor="auth-identifier">Email or username</label>
          <input id="auth-identifier" autoComplete="username" autoCapitalize="none" placeholder="you@example.com"
            required value={identifier} onChange={(event) => setIdentifier(event.target.value)} /></div>}
        <div className="auth-field">
          <label htmlFor="auth-password">Password</label>
          <div className="password-wrap">
            <input id="auth-password" type={showPassword ? "text" : "password"} aria-invalid={!!error}
              autoComplete={isRegister ? "new-password" : "current-password"} minLength={isRegister ? 12 : 1}
              required value={password} onChange={(event) => { setPassword(event.target.value); setError(""); }} />
            <button type="button" className="password-toggle" aria-pressed={showPassword}
              aria-label={showPassword ? "Hide password" : "Show password"} onClick={() => setShowPassword((value) => !value)}>
              <Icon name={showPassword ? "eyeOff" : "eye"} width={17} height={17} />
            </button>
          </div>
        </div>
        <button className="auth-submit" disabled={saving}>
          {saving ? "Please wait…" : isRegister ? "Create account" : "Sign in"}
        </button>
        {error && <p className="auth-error" role="alert">{error}</p>}
      </form>
      <p className="auth-switch">
        {isRegister ? "Already have an account?" : `New to ${siteName}?`}{" "}
        <Link to={isRegister ? "/login" : "/register"} state={location.state}>
          {isRegister ? "Sign in" : "Create an account"}
        </Link>
      </p>
    </section>
  </main>;
}
