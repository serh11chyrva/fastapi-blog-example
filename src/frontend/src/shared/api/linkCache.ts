import type { LinkResolution } from "./types";

type Entry = { result: LinkResolution; until: number };
const cache = new Map<string, Entry>();
const listeners = new Map<string, Set<() => void>>();

export function normalizedLinkUrl(url: string) {
  const target = new URL(url);
  target.hash = "";
  return target.href;
}

export function cachedLink(url: string) { return cache.get(normalizedLinkUrl(url)); }

export function storeLinkResult(url: string, result: LinkResolution): LinkResolution {
  const key = normalizedLinkUrl(url);
  const previous = cache.get(key);
  if (previous?.result.status === "ready" && result.status !== "ready") return previous.result;
  cache.delete(key);
  cache.set(key, { result, until: Date.now() + (result.status === "pending" ? 1500 : 60000) });
  if (cache.size > 200) cache.delete(cache.keys().next().value!);
  listeners.get(key)?.forEach((listener) => listener());
  return result;
}

export function subscribeLink(url: string, listener: () => void) {
  const key = normalizedLinkUrl(url);
  const group = listeners.get(key) ?? new Set<() => void>();
  group.add(listener);
  listeners.set(key, group);
  return () => {
    group.delete(listener);
    if (!group.size) listeners.delete(key);
  };
}

export function seedPublicationLinks(value: unknown) {
  if (!value || typeof value !== "object") return;
  if (Array.isArray(value)) { value.forEach(seedPublicationLinks); return; }
  const record = value as Record<string, unknown>;
  if (record.link_resolutions && typeof record.link_resolutions === "object") {
    for (const [url, result] of Object.entries(record.link_resolutions as Record<string, LinkResolution>)) {
      if (result && ["ready", "pending", "fallback"].includes(result.status)) storeLinkResult(url, result);
    }
  }
  for (const [key, child] of Object.entries(record)) {
    if (key !== "link_resolutions" && key !== "body") seedPublicationLinks(child);
  }
}
