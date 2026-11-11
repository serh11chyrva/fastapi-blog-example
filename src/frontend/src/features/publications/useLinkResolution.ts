import { useEffect, useSyncExternalStore } from "react";
import { api } from "../../shared/api/client";
import { cachedLink, normalizedLinkUrl, storeLinkResult, subscribeLink } from "../../shared/api/linkCache";
import type { LinkResolution } from "../../shared/api/types";

const pending = new Map<string, Promise<LinkResolution>>();

export function resolveCachedLink(url: string): Promise<LinkResolution> {
  const target = normalizedLinkUrl(url);
  const entry = cachedLink(target);
  if (entry && entry.until > Date.now()) return Promise.resolve(entry.result);
  const existing = pending.get(target);
  if (existing) return existing;
  const promise = api<LinkResolution>(`/links/resolved?${new URLSearchParams({ url: target })}`, { cache: "no-store" })
    .then((result) => storeLinkResult(target, result))
    .finally(() => { if (pending.get(target) === promise) pending.delete(target); });
  pending.set(target, promise);
  return promise;
}

export function useLinkResolution(url: string, enabled = true) {
  const target = normalizedLinkUrl(url);
  const result = useSyncExternalStore(
    (listener) => subscribeLink(target, listener),
    () => cachedLink(target)?.result,
    () => undefined,
  );
  useEffect(() => {
    if (!enabled) return;
    let active = true;
    let timer: ReturnType<typeof setTimeout> | undefined;
    let attempts = 0;
    async function read() {
      try {
        const current = await resolveCachedLink(target);
        if (active && current.status === "pending" && ++attempts < 10)
          timer = setTimeout(() => void read(), 3000);
      } catch { /* Saved card content remains available when metadata cannot be loaded. */ }
    }
    void read();
    return () => { active = false; clearTimeout(timer); };
  }, [target, enabled]);
  return result;
}
