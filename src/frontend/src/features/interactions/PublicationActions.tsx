import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { useApp } from "../../app/AuthProvider";
import { api, errorMessage } from "../../shared/api/client";
import type { InteractionAction, InteractionSummary, PublicationKind } from "../../shared/api/types";
import { interactionEvent, notifyInteractionChange, publicationPath } from "./events";
import type { InteractionChange } from "./events";

export function PublicationActions({ kind, id, onComments, onChanged }: {
  kind: PublicationKind;
  id: string;
  onComments: () => void;
  onChanged?: (action: InteractionAction, enabled: boolean) => void;
}) {
  const { user } = useApp();
  const [summary, setSummary] = useState<InteractionSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [pending, setPending] = useState<InteractionAction | null>(null);
  const [loadError, setLoadError] = useState("");
  const [actionError, setActionError] = useState("");
  const [version, setVersion] = useState(0);
  const mutation = useRef(false);
  const active = useRef<AbortController | null>(null);
  const path = publicationPath(kind, id);

  useEffect(() => {
    const controller = new AbortController();
    active.current = controller;
    mutation.current = false;
    setSummary(null);
    setPending(null);
    setActionError("");
    return () => controller.abort();
  }, [path, user?.id]);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setLoadError("");
    api<InteractionSummary>(`${path}/interactions`, { signal: controller.signal, cache: "no-store" })
      .then((value) => { if (!controller.signal.aborted) setSummary(value); })
      .catch((reason: unknown) => { if (!controller.signal.aborted) setLoadError(errorMessage(reason)); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [path, user?.id, version]);

  useEffect(() => {
    function changed(event: Event) {
      const detail = (event as CustomEvent<InteractionChange>).detail;
      if (detail.kind === kind && detail.id === id) setVersion((value) => value + 1);
    }
    window.addEventListener(interactionEvent, changed);
    return () => window.removeEventListener(interactionEvent, changed);
  }, [kind, id]);

  async function change(action: InteractionAction, enabled: boolean) {
    const controller = active.current;
    if (!user || mutation.current || loading || !controller) return;
    mutation.current = true;
    setPending(action);
    setActionError("");
    try {
      await api(`${path}/${action}`, { method: enabled ? "PUT" : "DELETE", signal: controller.signal });
      if (!controller.signal.aborted) {
        notifyInteractionChange({ kind, id, action, enabled });
        onChanged?.(action, enabled);
      }
    } catch (reason) {
      if (!controller.signal.aborted) {
        setActionError(`${errorMessage(reason)} Check the current state before retrying.`);
        setVersion((value) => value + 1);
      }
    } finally {
      if (!controller.signal.aborted) {
        mutation.current = false;
        setPending(null);
      }
    }
  }

  const disabled = !user || !summary || loading || !!loadError || pending !== null;
  return <div className="mt-4 border-t border-neutral-200 pt-3">
    <div className="flex flex-wrap items-center gap-2" aria-busy={loading || pending !== null}>
      <button className="interaction-button" disabled={disabled} aria-pressed={summary?.liked ?? false}
        onClick={() => void change("like", !summary?.liked)}>
        {summary?.liked ? "♥ Liked" : "♡ Like"} {summary?.likes_count ?? "…"}
      </button>
      <button className="interaction-button" disabled={disabled} aria-pressed={summary?.saved ?? false}
        onClick={() => void change("save", !summary?.saved)}>
        {summary?.saved ? "✓ Saved" : "+ Save"}
      </button>
      {kind === "micro_post" && <button className="interaction-button" disabled={disabled}
        aria-pressed={summary?.reposted ?? false} onClick={() => void change("repost", !summary?.reposted)}>
        {summary?.reposted ? "↻ Reposted" : "↻ Repost"} {summary?.reposts_count ?? "…"}
      </button>}
      <button className="interaction-button" onClick={onComments}>
        {kind === "micro_post" ? "Replies" : "Comments"} {summary?.comments_count ?? "…"}
      </button>
      {pending && <span className="text-xs text-neutral-500" role="status">Saving…</span>}
      {!user && <Link className="text-xs underline" to="/login">Log in to join in</Link>}
    </div>
    {loadError && <p role="alert" className="mt-2 text-sm">{loadError}{" "}
      <button className="underline" onClick={() => setVersion((value) => value + 1)}>Retry</button>
    </p>}
    {actionError && <p role="alert" className="mt-2 text-sm">{actionError}</p>}
  </div>;
}
