export function mergeListItems<T>(previous: T[], incoming: T[], identify: (item: T) => string): T[] {
  const seen = new Set(previous.map(identify));
  return [...previous, ...incoming.filter((item) => {
    const key = identify(item);
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  })];
}

export function itemId(item: { id: string }) { return item.id; }
