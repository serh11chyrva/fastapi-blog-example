const relative = new Intl.RelativeTimeFormat("en", { numeric: "auto" });
const compactDate = new Intl.DateTimeFormat("en", { month: "short", day: "numeric" });
const longDate = new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "long", year: "numeric" });

export function relativeDate(value: string) {
  const date = new Date(value);
  const seconds = Math.round((date.getTime() - Date.now()) / 1000);
  if (Math.abs(seconds) < 60) return "just now";
  if (Math.abs(seconds) < 3600) return relative.format(Math.round(seconds / 60), "minute");
  if (Math.abs(seconds) < 86400) return relative.format(Math.round(seconds / 3600), "hour");
  if (Math.abs(seconds) < 604800) return relative.format(Math.round(seconds / 86400), "day");
  return compactDate.format(date);
}

export function publicationDate(value: string) {
  return longDate.format(new Date(value));
}
