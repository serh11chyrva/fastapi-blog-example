const relative = new Intl.RelativeTimeFormat("en", { numeric: "always" });
const day = 24 * 60 * 60;
const relativeUnits: [Intl.RelativeTimeFormatUnit, number][] = [
  ["year", 365 * day],
  ["month", 30 * day],
  ["week", 7 * day],
  ["day", day],
  ["hour", 60 * 60],
  ["minute", 60],
];
const longDate = new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "long", year: "numeric" });
const dateTime = new Intl.DateTimeFormat("en-GB", { dateStyle: "long", timeStyle: "long" });

export function relativeDate(value: string) {
  const seconds = (Date.parse(value) - Date.now()) / 1000;
  const unit = relativeUnits.find(([, duration]) => Math.abs(seconds) >= duration);
  return unit ? relative.format(Math.trunc(seconds / unit[1]), unit[0]) : "just now";
}

export function publicationDate(value: string) {
  return longDate.format(new Date(value));
}

export function exactDateTime(value: string) {
  return dateTime.format(new Date(value));
}
