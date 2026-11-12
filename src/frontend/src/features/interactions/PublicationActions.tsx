import { useEffect, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { Icon } from "../../shared/ui/Icon";
import { useApp } from "../../app/AuthProvider";
import { api, errorMessage } from "../../shared/api/client";
import type { InteractionAction, InteractionSummary, PublicationKind } from "../../shared/api/types";
import { interactionEvent, notifyInteractionChange, publicationPath } from "./events";
import type { InteractionChange } from "./events";
import { Skeleton } from "../../shared/ui/Skeleton";

export function PublicationActions({ kind, id, onComments, commentsOpen, onShare, copied, onChanged }: {
  kind: PublicationKind;
  id: string;
  onComments: () => void;
  commentsOpen?: boolean;
  onShare?: () => void;
  copied?: boolean;
  onChanged?: (action: InteractionAction, enabled: boolean) => void;
}) {
  const { user } = useApp();
  const navigate = useNavigate();
  const location = useLocation();
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
    if (!user) {
      navigate("/login", { state: { from: location.pathname + location.search + location.hash } });
      return;
    }
    if (mutation.current || loading || !controller) return;
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

  const disabled = !!user && (!summary || loading || !!loadError || pending !== null);
  const missingCount = loading ? <Skeleton className="skeleton-count" /> : "—";
  return <div className="publication-actions">
    <div className="post-actions" aria-busy={loading || pending !== null}>
      <button type="button" className="engage engage-like" disabled={disabled} aria-pressed={summary?.liked ?? false}
        aria-label={summary?.liked ? "Unlike" : "Like"} title={summary?.liked ? "Unlike" : "Like"}
        onClick={() => void change("like", !summary?.liked)}>
        <Icon name="heart" />{summary?.likes_count ?? missingCount}
      </button>
      {kind === "micro_post" && <button type="button" className="engage engage-repost" disabled={disabled}
        aria-label={summary?.reposted ? "Undo repost" : "Repost"} title={summary?.reposted ? "Undo repost" : "Repost"}
        aria-pressed={summary?.reposted ?? false} onClick={() => void change("repost", !summary?.reposted)}>
        <Icon name="repost" />{summary?.reposts_count ?? missingCount}
      </button>}
      <button type="button" className="engage" aria-expanded={commentsOpen} onClick={onComments}
        aria-label={kind === "micro_post" ? "Replies" : "Comments"} title={kind === "micro_post" ? "Replies" : "Comments"}>
        <Icon name="comment" />{summary?.comments_count ?? missingCount}
      </button>
      <span className="actions-spacer" />
      {onShare && <button type="button" className="engage" onClick={onShare}
        aria-label={copied ? "Link copied" : "Share"} title={copied ? "Link copied" : "Share"}>
        <Icon name={copied ? "check" : "share"} />
      </button>}
      <button type="button" className="engage engage-save" disabled={disabled} aria-pressed={summary?.saved ?? false}
        aria-label={summary?.saved ? "Remove bookmark" : "Bookmark"} title={summary?.saved ? "Remove bookmark" : "Bookmark"}
        onClick={() => void change("save", !summary?.saved)}><Icon name="bookmark" /></button>
    </div>
    {loading && !summary && <span className="sr-only" role="status">Loading reactions…</span>}
    {copied && <span className="sr-only" role="status">Link copied.</span>}
    {pending && <span className="sr-only" role="status">Saving…</span>}
    {loadError && <p className="notice-error" role="alert">{loadError}{" "}
      <button className="text-link" onClick={() => setVersion((value) => value + 1)}>Retry</button>
    </p>}
    {actionError && <p className="notice-error" role="alert">{actionError}</p>}
  </div>;
}
