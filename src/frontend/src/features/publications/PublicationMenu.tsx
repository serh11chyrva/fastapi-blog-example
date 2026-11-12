import { useEffect, useRef, useState } from "react";
import type { ReactNode, RefObject } from "react";
import { useApp } from "../../app/AuthProvider";
import { api, errorMessage } from "../../shared/api/client";
import type { Article, MicroPost, PublicationBase, PublicationKind } from "../../shared/api/types";
import { Icon } from "../../shared/ui/Icon";
import { notifyPublicationStateChange, publicationPath } from "../interactions/events";

export function PublicationMenu({ item, onChanged, onReconciled, children, menuRef, disabled = false, readOnly = false }: {
  item: PublicationBase & { kind: PublicationKind; status?: Article["status"] };
  onChanged?: (publication: Article | MicroPost) => void;
  onReconciled?: (publication: Article | MicroPost) => void;
  children?: ReactNode;
  menuRef?: RefObject<HTMLDetailsElement | null>;
  disabled?: boolean;
  readOnly?: boolean;
}) {
  const { user } = useApp();
  const ownMenu = useRef<HTMLDetailsElement>(null);
  const menu = menuRef ?? ownMenu;
  const [current, setCurrent] = useState(item);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const pending = useRef(false);
  const active = useRef<AbortController | null>(null);
  useEffect(() => { setCurrent(item); }, [item]);
  useEffect(() => {
    const controller = new AbortController();
    active.current = controller;
    pending.current = false;
    setBusy(false);
    setError("");
    return () => controller.abort();
  }, [item.id, user?.id]);

  async function change(action: "archive" | "pin", enabled: boolean) {
    const controller = active.current;
    if (pending.current || disabled || !controller || user?.id !== item.owner_id) return;
    pending.current = true;
    setBusy(true);
    setError("");
    const path = publicationPath(item.kind, item.id);
    try {
      const updated = await api<Article | MicroPost>(`${path}/${action}`, {
        method: enabled ? "PUT" : "DELETE", signal: controller.signal,
      });
      if (controller.signal.aborted) return;
      setCurrent(updated);
      menu.current?.removeAttribute("open");
      notifyPublicationStateChange({ kind: item.kind, id: item.id });
      onChanged?.(updated);
    } catch (reason) {
      if (controller.signal.aborted) return;
      setError(errorMessage(reason));
      try {
        const updated = await api<Article | MicroPost>(path, { signal: controller.signal, cache: "no-store" });
        if (!controller.signal.aborted) {
          setCurrent(updated);
          onReconciled?.(updated);
        }
      } catch { /* Keep the original mutation error visible until an explicit retry. */ }
    } finally {
      if (!controller.signal.aborted) { pending.current = false; setBusy(false); }
    }
  }

  const own = user?.id === item.owner_id;
  const published = item.kind === "micro_post" || !current.status || current.status === "published";
  return <>
    <details className="post-menu" ref={menu} onKeyDown={(event) => {
      if (event.key === "Escape") {
        menu.current?.removeAttribute("open");
        menu.current?.querySelector("summary")?.focus();
      }
    }}>
      <summary className="icon-button" aria-label="More publication actions" title="More actions"><Icon name="more" /></summary>
      <div className="post-menu-list" aria-busy={busy}>
        {children}
        {own && published && <>
          {!current.archived_at && <button type="button" disabled={disabled || busy || ((readOnly || current.read_only) && !current.pinned_at)}
            onClick={() => void change("pin", !current.pinned_at)}>{current.pinned_at ? "Unpin" : "Pin"}</button>}
          <button type="button" disabled={disabled || busy}
            onClick={() => void change("archive", !current.archived_at)}>{current.archived_at ? "Unarchive" : "Archive"}</button>
        </>}
      </div>
    </details>
    {busy && <span className="sr-only" role="status">Saving publication state…</span>}
    {error && <span className="notice-error publication-state-error" role="alert">{error}</span>}
  </>;
}
