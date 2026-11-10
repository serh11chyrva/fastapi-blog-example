import { usePageTitle } from "../../app/usePageTitle";
import { useApp } from "../../app/AuthProvider";
import { useEffect, useState } from "react";
import type { OwnProfile, OwnerBadge, ProfileLinkInput } from "../../shared/api/types";
import { api, errorMessage } from "../../shared/api/client";
import { Navigate } from "react-router-dom";
import type { FormEvent } from "react";
import { useImageUploader } from "../../shared/uploads/uploadImages";
import { Avatar } from "../../shared/ui/Avatar";
import { BadgeIcon } from "./BadgeIcon";
export function ProfileSettingsPage() {
  usePageTitle("Profile settings");
  const { user } = useApp();
  const [profile, setProfile] = useState<OwnProfile | null>(null);
  const [displayName, setDisplayName] = useState("");
  const [bio, setBio] = useState("");
  const [location, setLocation] = useState("");
  const [links, setLinks] = useState<ProfileLinkInput[]>([]);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [uploading, setUploading] = useState(false);
  const [saving, setSaving] = useState(false);
  const uploadImages = useImageUploader();
  const [pendingAvatar, setPendingAvatar] = useState<File | null>(null);
  const [pendingBanner, setPendingBanner] = useState<File | null>(null);
  async function loadProfile() {
    const value = await api<OwnProfile>("/me/profile");
    setProfile(value);
    setDisplayName(value.display_name);
    setBio(value.bio);
    setLocation(value.location);
    setLinks(value.links.map(({ version, id, label, url }) => ({ version, id, label, url })));
  }
  useEffect(() => {
    if (user)
      void loadProfile().catch((reason) => setError(errorMessage(reason)));
  }, [user]);
  if (!user)
    return <Navigate to="/login" replace />;
  async function save(event: FormEvent) {
    event.preventDefault(); if (!profile || saving || uploading)
      return; setSaving(true); setNotice(""); setError(""); try {
        const updated = await api<OwnProfile>("/me/profile", { method: "PATCH", body: JSON.stringify({ revision: profile.revision, display_name: displayName, bio, location, links }) });
        setProfile(updated);
        setDisplayName(updated.display_name);
        setBio(updated.bio);
        setLocation(updated.location);
        setLinks(updated.links.map(({ version, id, label, url }) => ({ version, id, label, url })));
        setNotice("Your profile has been updated.");
      }
    catch (reason) {
      setError(errorMessage(reason));
    }
    finally {
      setSaving(false);
    }
  }
  async function toggleBadge(badge: OwnerBadge) {
    if (!profile || saving || uploading)
      return;
    setSaving(true);
    setError("");
    setNotice("");
    try {
      const updated = await api<OwnProfile>(`/me/badges/${badge.code}`, { method: "PATCH", body: JSON.stringify({ revision: profile.revision, enabled: !badge.preferences.enabled }) });
      setProfile(updated);
      setNotice("Badge visibility has been updated.");
    }
    catch (reason) {
      setError(errorMessage(reason));
    }
    finally {
      setSaving(false);
    }
  }
  async function upload(event: FormEvent<HTMLInputElement>) {
    const file = event.currentTarget.files?.[0];
    event.currentTarget.value = "";
    if (file) await uploadAvatar(file);
  }
  async function uploadAvatar(file: File) {
    if (uploading || saving || !profile) return;
    setPendingAvatar(file);
    setUploading(true);
    setError("");
    setNotice("");
    try {
      const updated = await uploadImages<OwnProfile>("/me/avatar", [file]);
      setProfile(updated.revision === profile.revision + 1 ? updated : { ...profile, avatars: updated.avatars });
      setPendingAvatar(null);
      setNotice("Your avatar has been updated.");
    }
    catch (reason) {
      setError(errorMessage(reason));
    }
    finally {
      setUploading(false);
    }
  }
  async function changeBanner(file?: File) {
    if (uploading || saving || !profile) return;
    setUploading(true);
    setError("");
    setNotice("");
    if (file) setPendingBanner(file);
    try {
      let updated: OwnProfile;
      if (file) {
        updated = await uploadImages<OwnProfile>("/me/banner", [file]);
      } else {
        await api("/me/banner", { method: "DELETE" });
        updated = await api<OwnProfile>("/me/profile");
      }
      setProfile(updated.revision === profile.revision + 1 ? updated : { ...profile, banner_url: updated.banner_url });
      setPendingBanner(null);
      setNotice(file ? "Your profile banner has been updated." : "Your profile banner has been removed.");
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setUploading(false);
    }
  }
  function updateLink(index: number, key: "label" | "url", value: string) { setLinks((current) => current.map((item, itemIndex) => itemIndex === index ? { ...item, [key]: value } : item)); }
  return <div className="utility-page space-y-4">
    <div>
      <p className="eyebrow">Your account</p>
      <h1 className="page-title">Profile settings</h1>
    </div>
    <form onSubmit={save} className="surface space-y-5 p-5 sm:p-7">
      <fieldset className="contents" disabled={saving || uploading}>
        <div className="flex items-center gap-4">
          <Avatar src={profile?.avatars.original} name={displayName || user.display_name} size="lg" />
          <label className="button-secondary cursor-pointer">
            {uploading ? "Uploading…" : "Upload avatar"}
            <input className="sr-only" type="file" accept="image/jpeg,image/png,image/webp" onChange={upload} disabled={uploading} />
          </label>
          {pendingAvatar && <button type="button" className="button-secondary"
            onClick={() => void uploadAvatar(pendingAvatar)}>Retry avatar upload</button>}
          <span className="text-xs text-slate-400">JPEG, PNG, or WebP · up to 5 MB</span>
        </div>
        <div className="space-y-3">
          {profile?.banner_url && <img className="h-32 w-full object-cover" src={profile.banner_url} alt="Profile banner" />}
          <div className="flex flex-wrap gap-2">
            <label className="button-secondary cursor-pointer">
              {profile?.banner_url ? "Replace banner" : "Upload banner"}
              <input className="sr-only" type="file" accept="image/jpeg,image/png,image/webp"
                onChange={(event) => {
                  const file = event.target.files?.[0];
                  event.target.value = "";
                  if (file) void changeBanner(file);
                }} />
            </label>
            {profile?.banner_url && <button type="button" className="button-quiet" onClick={() => void changeBanner()}>Remove banner</button>}
            {pendingBanner && <button type="button" className="button-secondary"
              onClick={() => void changeBanner(pendingBanner)}>Retry banner upload</button>}
          </div>
        </div>
        <label className="form-label block">Location<input className="field mt-1.5" maxLength={80}
          value={location} onChange={(event) => setLocation(event.target.value)} /></label>
        <label className="form-label block">Username<div className="field mt-1.5 bg-slate-50 text-slate-500">@{user.username}</div></label>
        <label className="form-label block">Public name<input className="field mt-1.5" maxLength={64} value={displayName} onChange={(event) => setDisplayName(event.target.value)} /></label>
        <label className="form-label block">Bio<textarea className="field mt-1.5 min-h-24 resize-y" maxLength={280} value={bio} onChange={(event) => setBio(event.target.value)} /></label>
        <div>
          <div className="mb-2 flex items-center justify-between">
            <span className="form-label">Profile links</span>
            <button type="button" className="text-sm font-semibold text-slate-700" onClick={() => setLinks((current) => current.length < 8 ? [...current, { label: "", url: "https://" }] : current)}>Add link</button>
          </div>
          <div className="space-y-2">
            {links.map((link, index) => <div className="grid gap-2 sm:grid-cols-[150px_1fr_auto]" key={index}>
              <input className="field" placeholder="Label" maxLength={32} value={link.label} onChange={(event) => updateLink(index, "label", event.target.value)} />
              <input className="field" placeholder="https://example.com" value={link.url} onChange={(event) => updateLink(index, "url", event.target.value)} />
              <button type="button" className="button-quiet" onClick={() => setLinks((current) => current.filter((_, itemIndex) => itemIndex !== index))}>Remove</button>
            </div>)}
          </div>
        </div>
        {profile && profile.badges.length > 0 && <div>
          <p className="form-label mb-2">Badge visibility</p>
          <div className="space-y-2">
            {profile.badges.map((badge) => <label className="flex items-center gap-3 text-sm" key={badge.code}>
              <input type="checkbox" checked={badge.preferences.enabled} disabled={!badge.permissions.can_disable && badge.preferences.enabled} onChange={() => void toggleBadge(badge)} />
              <BadgeIcon badge={badge} />
              <span>
                {badge.payload.label}
              </span>
              {!badge.permissions.can_disable && <span className="text-xs text-slate-500">Required badge</span>}
            </label>)}
          </div>
        </div>}
        {notice && <div className="notice-success">
          {notice}
        </div>}
        {error && <div className="notice-error">
          {error}
          <button type="button" className="ml-2 underline" onClick={() => { void loadProfile().then(() => setError("")).catch((reason) => setError(errorMessage(reason))); }}>Reload saved profile (discard form edits)</button>
        </div>}
        <button className="button-primary" disabled={saving || uploading || !profile}>
          {saving ? "Saving…" : "Save profile"}
        </button>
      </fieldset>
    </form>
  </div>;
}
