import { useLayoutEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import { useDisclosureAnimation } from "../hooks/useDisclosureAnimation";

export function Collapsible({ open, children, id, className = "", animateInitial = false, instant = false }: {
  open: boolean;
  children: ReactNode;
  id?: string;
  className?: string;
  animateInitial?: boolean;
  instant?: boolean;
}) {
  const panel = useRef<HTMLDivElement>(null);
  const content = useRef<HTMLDivElement>(null);
  const lastFocused = useRef<HTMLElement | null>(null);
  const [visited, setVisited] = useState(open);
  useDisclosureAnimation(panel, content, lastFocused, open, animateInitial, instant);

  useLayoutEffect(() => {
    if (open) setVisited(true);
  }, [open]);

  return <div ref={panel} id={id} className="collapsible"
    onFocusCapture={(event) => { lastFocused.current = event.target; }}>
    <div ref={content} className="collapsible-content">
      {(open || visited) && (className ? <div className={className}>{children}</div> : children)}
    </div>
  </div>;
}
