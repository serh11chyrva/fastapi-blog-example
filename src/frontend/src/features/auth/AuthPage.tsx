import { Link, useLocation, useNavigate } from "react-router-dom";
import { useApp } from "../../app/AuthProvider";
import { useState } from "react";
import type { FormEvent } from "react";
import { api, errorMessage } from "../../shared/api/client";
import type { User } from "../../shared/api/types";
export function AuthPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const { setUser } = useApp();
  const isRegister = location.pathname === "/register";
  const [identifier, setIdentifier] = useState("");
  const [email, setEmail] = useState("");
  const [username, setUsername] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  async function submit(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError("");
    try {
      const user = isRegister
        ? await api<User>("/auth/register", { method: "POST", body: JSON.stringify({ email, username, display_name: displayName, password }) })
        : await api<User>("/auth/login", { method: "POST", body: JSON.stringify({ identifier, password }) });
      setUser(user);
      navigate("/");
    }
    catch (reason) {
      setError(errorMessage(reason));
    }
    finally {
      setSaving(false);
    }
  }
  return <div className="mx-auto max-w-md">
    <div className="surface p-6 sm:p-8">
      <p className="eyebrow">Join commonplace</p>
      <h1 className="mt-2 text-2xl font-semibold tracking-tight text-slate-900">
        {isRegister ? "Make room for your ideas" : "Welcome back"}
      </h1>
      <p className="mt-2 text-sm leading-6 text-slate-500">
        {isRegister ? "Create an account to publish, follow writers, and save a place for longer stories." : "Sign in with your email address or username."}
      </p>

      <form onSubmit={submit} className="mt-6 space-y-4">
        {isRegister ? <>
          <label className="form-label">Email<input className="field mt-1.5" type="email" autoComplete="email" required value={email} onChange={(event) => setEmail(event.target.value)} /></label>
          <label className="form-label">Username<input className="field mt-1.5" autoComplete="username" minLength={3} maxLength={24} placeholder="your_handle" required value={username} onChange={(event) => setUsername(event.target.value)} /></label>
          <label className="form-label">Public name<input className="field mt-1.5" autoComplete="name" maxLength={64} required value={displayName} onChange={(event) => setDisplayName(event.target.value)} /></label>
        </> : <label className="form-label">Email or username<input className="field mt-1.5" autoComplete="username" required value={identifier} onChange={(event) => setIdentifier(event.target.value)} /></label>}

        <label className="form-label">Password<input className="field mt-1.5" type="password" autoComplete={isRegister ? "new-password" : "current-password"} minLength={isRegister ? 12 : 1} required value={password} onChange={(event) => setPassword(event.target.value)} /></label>

        {error && <div className="notice-error">
          {error}
        </div>}
        <button className="button-primary w-full justify-center" disabled={saving}>
          {saving ? "Please wait…" : isRegister ? "Create account" : "Log in"}
        </button>

      </form>
      <p className="mt-5 text-center text-sm text-slate-500">
        {isRegister ? "Already have an account?" : "New to commonplace?"}
        <Link className="font-semibold text-slate-700 hover:text-slate-900" to={isRegister ? "/login" : "/register"}>
          {isRegister ? "Log in" : "Create an account"}
        </Link>
      </p>
    </div>
  </div>;
}
