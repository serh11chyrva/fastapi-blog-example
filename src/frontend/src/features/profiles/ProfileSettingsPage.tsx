import { useCallback, useEffect, useRef, useState } from "react";
import type { ChangeEvent, FormEvent } from "react";
import { Navigate } from "react-router-dom";
import { useApp } from "../../app/AuthProvider";
import { usePageTitle } from "../../app/usePageTitle";
import { api, errorMessage } from "../../shared/api/client";
import type { OwnProfile, OwnerBadge } from "../../shared/api/types";
import { Avatar } from "../../shared/ui/Avatar";
import { useImageUploader, validateImages } from "../../shared/uploads/uploadImages";
import { BadgeIcon } from "./BadgeIcon";
import { ProfileImageCropDialog } from "./ProfileImageCropDialog";
import type { ProfileImageKind } from "./ProfileImageCropDialog";
import { ProfileLinksEditor } from "./ProfileLinksEditor";
import type { ProfileLinkDraft } from "./ProfileLinksEditor";

const imageTypes = "image/jpeg,image/png,image/webp";

export function ProfileSettingsPage() {
  usePageTitle("Profile settings");
  const { user, updateAccountProfile } = useApp();
  const [profile, setProfile] = useState<OwnProfile | null>(null);
  const [displayName, setDisplayName] = useState("");
  const [bio, setBio] = useState("");
  const [location, setLocation] = useState("");
  const [links, setLinks] = useState<ProfileLinkDraft[]>([]);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState<ProfileImageKind | null>(null);
  const [saving, setSaving] = useState(false);
  const [crop, setCrop] = useState<{ kind: ProfileImageKind; file: File } | null>(null);
  const [pending, setPending] = useState<Partial<Record<ProfileImageKind, File>>>({});
  const activeLoad = useRef<AbortController | null>(null);
  const uploadImages = useImageUploader();

  const applyProfile = useCallback((value: OwnProfile) => {
    setProfile(value);
    setDisplayName(value.display_name);
    setBio(value.bio);
    setLocation(value.location);
    setLinks(value.links.map(({ version, id, label, url }) => ({ key: id, link: { version, id, label, url } })));
    updateAccountProfile(value);
  }, [updateAccountProfile]);

  const loadProfile = useCallback(async () => {
    activeLoad.current?.abort();
    const controller = new AbortController();
    activeLoad.current = controller;
    setLoading(true);
    setError("");
    setNotice("");
    try {
      const value = await api<OwnProfile>("/me/profile", { signal: controller.signal });
      if (!controller.signal.aborted) applyProfile(value);
    } catch (reason) {
      if (!controller.signal.aborted) setError(errorMessage(reason));
    } finally {
      if (!controller.signal.aborted) setLoading(false);
    }
  }, [applyProfile]);

  useEffect(() => {
    if (user?.id) void loadProfile();
    return () => activeLoad.current?.abort();
  }, [user?.id, loadProfile]);

  if (!user) return <Navigate to="/login" replace />;

  const busy = loading || saving || uploading !== null;

  async function save(event: FormEvent) {
    event.preventDefault();
    if (!profile || busy || crop) return;
    setSaving(true);
    setNotice("");
    setError("");
    try {
      const updated = await api<OwnProfile>("/me/profile", {
        method: "PATCH",
        body: JSON.stringify({
          revision: profile.revision,
          display_name: displayName,
          bio,
          location,
          links: links.map(({ link }) => link),
        }),
      });
      applyProfile(updated);
      setNotice("Your profile has been updated.");
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setSaving(false);
    }
  }

  async function toggleBadge(badge: OwnerBadge) {
    if (!profile || busy) return;
    setSaving(true);
    setError("");
    setNotice("");
    try {
      const updated = await api<OwnProfile>(`/me/badges/${badge.code}`, {
        method: "PATCH",
        body: JSON.stringify({ revision: profile.revision, enabled: !badge.preferences.enabled }),
      });
      setProfile(updated);
      setNotice("Badge visibility has been updated.");
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setSaving(false);
    }
  }

  function selectImage(kind: ProfileImageKind, event: ChangeEvent<HTMLInputElement>) {
    const file = event.currentTarget.files?.[0];
    event.currentTarget.value = "";
    if (!file || busy) return;

    setNotice("");
    setError("");
    try {
      validateImages(kind === "avatar" ? "avatars" : "profile-banners", [file]);
      setCrop({ kind, file });
    } catch (reason) {
      setError(errorMessage(reason));
    }
  }

  async function changeImage({ kind, file }: { kind: ProfileImageKind; file: File } | { kind: "banner"; file: null }) {
    if (!profile || busy) return;
    setUploading(kind);
    setError("");
    setNotice("");
    if (file) setPending((current) => ({ ...current, [kind]: file }));
    try {
      let updated: OwnProfile;
      if (file) {
        updated = await uploadImages<OwnProfile>(`/me/${kind}`, [file]);
      } else {
        await api("/me/banner", { method: "DELETE" });
        updated = await api<OwnProfile>("/me/profile");
      }

      const media = kind === "avatar" ? { avatars: updated.avatars } : { banner_url: updated.banner_url };
      setProfile(updated.revision === profile.revision + 1 ? updated : { ...profile, ...media });
      updateAccountProfile(updated);
      setPending((current) => ({ ...current, [kind]: undefined }));
      setNotice(file ? `Your ${kind} has been updated.` : "Your profile banner has been removed.");
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setUploading(null);
    }
  }

  return <div className="utility-page space-y-4">
    <div>
      <p className="eyebrow">Your account</p>
      <h1 className="page-title">Profile settings</h1>
    </div>
    {loading && <p role="status">Loading profile…</p>}
    <form onSubmit={save} className="surface p-5 sm:p-7">
      <fieldset className="min-w-0 space-y-5" disabled={busy || !profile || crop !== null}>
        <section className="space-y-2" aria-label="Avatar">
          <h2 className="form-label">Avatar</h2>
          <div className="settings-media-actions">
            <Avatar src={profile ? profile.avatars.original : user.avatars?.original} name={displayName || user.display_name} size="lg" />
            <label className="button-secondary cursor-pointer">
              {uploading === "avatar" ? "Uploading…" : profile?.avatars.original ? "Replace avatar" : "Upload avatar"}
              <input className="sr-only" type="file" accept={imageTypes} onChange={(event) => selectImage("avatar", event)} />
            </label>
            {pending.avatar && <button type="button" className="button-secondary"
              onClick={() => { if (pending.avatar) void changeImage({ kind: "avatar", file: pending.avatar }); }}>
              Retry avatar upload
            </button>}
          </div>
          <p className="settings-media-hint">Square crop · JPEG, PNG, or WebP · up to 5 MiB</p>
        </section>
        <section className="space-y-2" aria-label="Banner">
          <h2 className="form-label">Banner</h2>
          {profile?.banner_url && <img className="settings-banner" src={profile.banner_url} alt="Profile banner" />}
          <div className="settings-media-actions">
            <label className="button-secondary cursor-pointer">
              {uploading === "banner" ? "Updating…" : profile?.banner_url ? "Replace banner" : "Upload banner"}
              <input className="sr-only" type="file" accept={imageTypes} onChange={(event) => selectImage("banner", event)} />
            </label>
            {profile?.banner_url && <button type="button" className="button-quiet"
              onClick={() => void changeImage({ kind: "banner", file: null })}>Remove banner</button>}
            {pending.banner && <button type="button" className="button-secondary"
              onClick={() => { if (pending.banner) void changeImage({ kind: "banner", file: pending.banner }); }}>
              Retry banner upload
            </button>}
          </div>
          <p className="settings-media-hint">4:1 crop · JPEG, PNG, or WebP · up to 5 MiB</p>
        </section>
        <label className="form-label">Username<input className="field bg-slate-50 text-slate-500" readOnly value={`@${user.username}`} /></label>
        <label className="form-label">Public name<input className="field" maxLength={64}
          value={displayName} onChange={(event) => setDisplayName(event.target.value)} /></label>
        <label className="form-label">Bio<textarea className="field min-h-24 resize-y" maxLength={280}
          value={bio} onChange={(event) => setBio(event.target.value)} /></label>
        <label className="form-label">Location<input className="field" maxLength={80}
          value={location} onChange={(event) => setLocation(event.target.value)} /></label>
        <ProfileLinksEditor links={links} onChange={setLinks} />
        {profile && profile.badges.length > 0 && <section className="space-y-2" aria-label="Badge visibility">
          <h2 className="form-label">Badge visibility</h2>
          {profile.badges.map((badge) => <label className="flex items-center gap-3 text-sm" key={badge.code}>
            <input type="checkbox" checked={badge.preferences.enabled}
              disabled={!badge.permissions.can_disable && badge.preferences.enabled} onChange={() => void toggleBadge(badge)} />
            <BadgeIcon badge={badge} />
            <span>{badge.payload.label}</span>
            {!badge.permissions.can_disable && <span className="text-xs text-slate-500">Required badge</span>}
          </label>)}
        </section>}
        <button className="button-primary">{saving ? "Saving…" : "Save profile"}</button>
      </fieldset>
      {notice && <p className="notice-success mt-4" role="status">{notice}</p>}
      {error && <div className="notice-error mt-4" role="alert">
        {error}
        <button type="button" className="ml-2 underline" disabled={busy} onClick={() => void loadProfile()}>
          Reload saved profile (discard form edits)
        </button>
      </div>}
    </form>
    {crop && <ProfileImageCropDialog file={crop.file} kind={crop.kind} onCancel={() => setCrop(null)}
      onApply={(file) => {
        setCrop(null);
        void changeImage({ kind: crop.kind, file });
      }} />}
  </div>;
}
