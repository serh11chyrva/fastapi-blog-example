import { useEffect, useState } from "react";
import { api } from "./client";
import type { ProfileCard } from "./types";

type CachedCard = { card: ProfileCard | null; expires: number };
type PendingCard = { promise: Promise<ProfileCard | null>; resolve: (card: ProfileCard | null) => void; reject: (reason: unknown) => void };
const cards = new Map<string, CachedCard>();
const pending = new Map<string, PendingCard>();
const queued = new Set<string>();
let scheduled = false;

async function flushCards() {
  scheduled = false;
  const ids = [...queued];
  queued.clear();
  for (let start = 0; start < ids.length; start += 50) {
    const batch = ids.slice(start, start + 50);
    try {
      const query = new URLSearchParams();
      batch.forEach((id) => query.append("user_id", id));
      const result = await api<ProfileCard[]>(`/profiles/cards?${query}`);
      const byId = new Map(result.map((card) => [card.id, card]));
      for (const id of batch) {
        const card = byId.get(id) ?? null;
        cards.set(id, { card, expires: Date.now() + 60_000 });
        pending.get(id)?.resolve(card);
        pending.delete(id);
      }
      while (cards.size > 500) cards.delete(cards.keys().next().value!);
    } catch (reason) {
      for (const id of batch) {
        pending.get(id)?.reject(reason);
        pending.delete(id);
      }
    }
  }
}

function loadCard(userId: string): Promise<ProfileCard | null> {
  const id = userId.toLowerCase();
  if (!/^[a-f\d]{24}$/.test(id)) return Promise.resolve(null);
  const cached = cards.get(id);
  if (cached && cached.expires > Date.now()) return Promise.resolve(cached.card);
  const existing = pending.get(id);
  if (existing) return existing.promise;
  let resolve!: PendingCard["resolve"];
  let reject!: PendingCard["reject"];
  const promise = new Promise<ProfileCard | null>((success, failure) => { resolve = success; reject = failure; });
  pending.set(id, { promise, resolve, reject });
  queued.add(id);
  if (!scheduled) {
    scheduled = true;
    setTimeout(() => { void flushCards(); }, 0);
  }
  return promise;
}

export function useProfileCard(userId: string) {
  const [result, setResult] = useState<{ id: string; card: ProfileCard | null }>();
  useEffect(() => {
    let active = true;
    loadCard(userId).then((card) => { if (active) setResult({ id: userId, card }); })
      .catch(() => { if (active) setResult({ id: userId, card: null }); });
    return () => { active = false; };
  }, [userId]);
  return result?.id === userId ? result.card : undefined;
}
