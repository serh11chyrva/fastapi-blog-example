import { useEffect, useState } from "react";
import { api } from "../../shared/api/client";
import type { Attachment } from "../../shared/api/types";

export type LinkResolution = {
  status: "pending" | "ready" | "fallback";
  card: Extract<Attachment, { type: "og_card" }>;
  attachment: Extract<Attachment, { type: "embed" | "og_card" }>;
  player_url: string | null;
};
const cache = new Map<string, { promise: Promise<LinkResolution>; until: number }>();

export function resolveCachedLink(url: string): Promise<LinkResolution> {
  const entry = cache.get(url);
  if (entry && entry.until > Date.now()) return entry.promise;
  const promise = api<LinkResolution>(`/links/resolved?${new URLSearchParams({ url })}`, { cache: "no-store" });
  cache.set(url, { promise, until: Date.now() + 1500 });
  if (cache.size > 200) cache.delete(cache.keys().next().value!);
  void promise.then((result) => {
    if (cache.get(url)?.promise === promise) cache.set(url, { promise, until: Date.now() + (result.status === "pending" ? 1500 : 60000) });
  }, () => { if (cache.get(url)?.promise === promise) cache.delete(url); });
  return promise;
}

export function useLinkResolution(url: string, enabled = true) {
  const [state, setState] = useState<{ url: string; result: LinkResolution }>();
  useEffect(() => {
    if (!enabled) return;
    let active = true;
    let timer: ReturnType<typeof setTimeout>;
    let attempts = 0;
    async function read() {
      try {
        const result = await resolveCachedLink(url);
        if (!active) return;
        setState({ url, result });
        if (result.status === "pending" && ++attempts < 10) timer = setTimeout(() => void read(), 3000);
      } catch { /* Saved card content remains available when metadata cannot be loaded. */ }
    }
    void read();
    return () => { active = false; clearTimeout(timer); };
  }, [url, enabled]);
  return state?.url === url ? state.result : undefined;
}
