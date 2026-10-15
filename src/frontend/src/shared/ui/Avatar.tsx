export function Avatar({ src, name, size = "md" }: {
  src?: string | null;
  name: string;
  size?: "sm" | "md" | "lg";
}) {
  const dimensions = size === "lg" ? "h-20 w-20 text-2xl" : size === "sm" ? "h-9 w-9 text-xs" : "h-11 w-11 text-sm";
  return src ? <img className={`${dimensions} rounded-full object-cover ring-1 ring-black/5`} src={src} alt={`${name}'s avatar`} /> : <div className={`${dimensions} flex shrink-0 items-center justify-center rounded-full bg-slate-100 font-semibold text-slate-700`}>
    {name.slice(0, 1).toUpperCase()}
  </div>;
}
