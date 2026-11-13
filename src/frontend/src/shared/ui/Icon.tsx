import type { ReactNode, SVGProps } from "react";

const drawings = {
  pulse: <path d="M2 12h5l3-7 4 14 3-7h5" />,
  sparkle: <><path d="M11 2l2.5 6.5L20 11l-6.5 2.5L11 20l-2.5-6.5L2 11l6.5-2.5Z" /><path d="M19 15v6m-3-3h6" /></>,
  home: <><path d="m3 10 9-7 9 7v10a1 1 0 0 1-1 1h-5v-7H9v7H4a1 1 0 0 1-1-1Z" /></>,
  search: <><circle cx="10.5" cy="10.5" r="6.5" /><path d="m16 16 5 5" /></>,
  following: <><circle cx="9" cy="8" r="3" /><path d="M3 20v-2a4 4 0 0 1 4-4h4a4 4 0 0 1 4 4v2m1-15a3 3 0 0 1 0 6m2 3a4 4 0 0 1 3 4v2" /></>,
  bookmark: <path d="M6 4h12v17l-6-4-6 4Z" />,
  book: <><path d="M12 6c-2-2-6-3-9-2v15c3-1 7 0 9 2 2-2 6-3 9-2V4c-3-1-7 0-9 2Zm0 0v15" /></>,
  user: <><circle cx="12" cy="8" r="4" /><path d="M4 21v-2a6 6 0 0 1 6-6h4a6 6 0 0 1 6 6v2" /></>,
  device: <><rect x="3" y="4" width="18" height="13" rx="2" /><path d="M8 21h8m-4-4v4" /></>,
  settings: <><path d="m10 3-.6 2.5-2 .9L5.1 5 3 7.1l1.4 2.3-.9 2L1 12v2.8l2.5.6.9 2L3 19.7 5.1 22l2.3-1.4 2 .9.6 2.5h3l.6-2.5 2-.9L18 22l2.1-2.3-1.4-2.3.9-2 2.4-.6V12l-2.4-.6-.9-2 1.4-2.3L18 5l-2.4 1.4-2-.9L13 3Z" transform="translate(1 -1) scale(.91)" /><circle cx="12" cy="12" r="3" /></>,
  menu: <path d="M4 6h16M4 12h16M4 18h16" />,
  alignLeft: <path d="M4 5h16M4 10h10M4 15h16M4 20h10" />,
  alignCenter: <path d="M4 5h16M7 10h10M4 15h16M7 20h10" />,
  alignRight: <path d="M4 5h16M10 10h10M4 15h16M10 20h10" />,
  alignJustify: <path d="M4 5h16M4 10h16M4 15h16M4 20h16" />,
  plus: <path d="M12 4v16M4 12h16" />,
  more: <><circle cx="5" cy="12" r="1" /><circle cx="12" cy="12" r="1" /><circle cx="19" cy="12" r="1" /></>,
  heart: <path d="M20.8 5.7a5 5 0 0 0-7 0L12 7.5l-1.8-1.8a5 5 0 0 0-7 7l1.8 1.8L12 21l7-6.5 1.8-1.8a5 5 0 0 0 0-7Z" />,
  repost: <><path d="m16 3 4 4-4 4m4-4H7a4 4 0 0 0-4 4v1m5 9-4-4 4-4m-4 4h13a4 4 0 0 0 4-4v-1" /></>,
  comment: <path d="M21 11.5a8.4 8.4 0 0 1-9 8.5 9 9 0 0 1-3.6-.7L3 21l1.6-4.9A8.1 8.1 0 0 1 3 11.5a8.5 8.5 0 0 1 9-8.5 8.4 8.4 0 0 1 9 8.5Z" />,
  share: <><path d="M12 15V3m-4 4 4-4 4 4M5 12v8h14v-8" /></>,
  external: <path d="M7 17 17 7M8 7h9v9" />,
  pushpin: <><path d="m16 3 5 5-3 2-2 5-3 1-5-5 1-3 5-2Z" /><path d="m11 13-8 8" /></>,
  archive: <><rect x="3" y="3" width="18" height="5" rx="1" /><path d="M5 8v13h14V8M10 12h4" /></>,
  pin: <><path d="M20 10c0 5-8 11-8 11S4 15 4 10a8 8 0 1 1 16 0Z" /><circle cx="12" cy="10" r="2.5" /></>,
  calendar: <><rect x="3" y="5" width="18" height="16" rx="2" /><path d="M7 3v4m10-4v4M3 10h18" /></>,
  link: <><path d="M10 13a4 4 0 0 0 6 0l4-4a4 4 0 0 0-6-6l-2 2m2 6a4 4 0 0 0-6 0l-4 4a4 4 0 0 0 6 6l2-2" /></>,
  check: <path d="m5 12 4 4L19 6" />,
  close: <path d="m6 6 12 12M18 6 6 18" />,
  left: <path d="m14 5-7 7 7 7" />,
  right: <path d="m10 5 7 7-7 7" />,
  chevron: <path d="m6 9 6 6 6-6" />,
  play: <path d="m8 4 12 8-12 8Z" />,
  music: <><path d="M9 18V5l11-2v13M9 9l11-2" /><ellipse cx="6" cy="18" rx="3" ry="2" /><ellipse cx="17" cy="16" rx="3" ry="2" /></>,
  image: <><rect x="3" y="3" width="18" height="18" rx="2" /><circle cx="8" cy="8" r="2" /><path d="m3 17 5-4 4 3 4-6 5 6" /></>,
  eye: <><path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7-10-7-10-7Z" /><circle cx="12" cy="12" r="3" /></>,
  eyeOff: <><path d="m3 3 18 18M10 5a10 10 0 0 1 2 0c6.4 0 10 7 10 7a18 18 0 0 1-3 3M6 6a18 18 0 0 0-4 6s3.6 7 10 7a10 10 0 0 0 5-1.4" /></>,
  code: <path d="m8 6-6 6 6 6m8-12 6 6-6 6m-2-15-4 18" />,
  write: <><path d="M12 20h9m-4.5-16a2 2 0 0 1 3 3L8 18l-4 1 1-4Z" /></>,
  grip: <><circle cx="9" cy="5" r="1" /><circle cx="15" cy="5" r="1" /><circle cx="9" cy="12" r="1" /><circle cx="15" cy="12" r="1" /><circle cx="9" cy="19" r="1" /><circle cx="15" cy="19" r="1" /></>,
  arrow: <path d="M21 12H3m7-7-7 7 7 7" />,
} satisfies Record<string, ReactNode>;

export type IconName = keyof typeof drawings;

export function Icon({ name, ...props }: { name: IconName } & SVGProps<SVGSVGElement>) {
  return <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.65"
    strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...props}>{drawings[name]}</svg>;
}
