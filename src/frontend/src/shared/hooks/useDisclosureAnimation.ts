import { useLayoutEffect, useRef } from "react";
import type { RefObject } from "react";

export function useDisclosureAnimation(
  panel: RefObject<HTMLDivElement | null>,
  content: RefObject<HTMLDivElement | null>,
  lastFocused: RefObject<HTMLElement | null>,
  open: boolean,
  animateInitial: boolean,
  instant: boolean,
) {
  const first = useRef(true);
  const opener = useRef<HTMLElement | null>(null);

  useLayoutEffect(() => {
    const element = panel.current;
    const inner = content.current;
    if (!element || !inner) return;

    const initial = first.current;
    first.current = false;
    const media = window.matchMedia("(prefers-reduced-motion: reduce)");
    let animation: Animation | null = null;
    let targetHeight = 0;

    function cancelAnimation() {
      if (!animation) return;
      animation.onfinish = null;
      animation.cancel();
      animation = null;
    }

    function settle() {
      cancelAnimation();
      element!.hidden = !open;
      element!.style.removeProperty("height");
      element!.style.removeProperty("overflow");
    }

    const active = document.activeElement;
    if (open && (!initial || animateInitial) && active instanceof HTMLElement
      && active !== document.body && !element.contains(active)) {
      opener.current = active;
      lastFocused.current = null;
    }
    if (!open && (element.contains(active)
      || active === document.body && lastFocused.current && element.contains(lastFocused.current))) {
      opener.current?.focus({ preventScroll: true });
      if (active instanceof HTMLElement && element.contains(document.activeElement)) active.blur();
      lastFocused.current = null;
    }

    // Move focus before hiding the panel from assistive technology.
    element.inert = !open;
    element.setAttribute("aria-hidden", String(!open));

    const from = element.hidden || initial && open && animateInitial ? 0 : element.getBoundingClientRect().height;
    element.hidden = false;

    const styles = getComputedStyle(element);
    const duration = Number.parseFloat(styles.getPropertyValue("--motion-expand")) || 220;
    const easing = styles.getPropertyValue("--motion-ease").trim() || "cubic-bezier(.2, 0, 0, 1)";

    function animateHeight(start: number, end: number) {
      cancelAnimation();
      targetHeight = end;
      if (Math.abs(start - end) < 1) { settle(); return; }
      element!.style.overflow = "hidden";
      element!.style.height = `${start}px`;
      animation = element!.animate([{ height: `${start}px` }, { height: `${end}px` }], {
        duration, easing, fill: "both",
      });
      animation.onfinish = settle;
    }

    if (instant || media.matches || initial && !animateInitial || typeof element.animate !== "function") {
      settle();
      return;
    }

    animateHeight(from, open ? inner.getBoundingClientRect().height : 0);
    const observer = typeof ResizeObserver === "undefined" ? null : new ResizeObserver(() => {
      if (!open || !animation) return;
      const height = inner.getBoundingClientRect().height;
      if (Math.abs(height - targetHeight) >= 1) animateHeight(element.getBoundingClientRect().height, height);
    });
    observer?.observe(inner);

    function motionChanged() {
      if (media.matches) settle();
    }
    media.addEventListener("change", motionChanged);

    return () => {
      observer?.disconnect();
      media.removeEventListener("change", motionChanged);
      if (animation) {
        // Preserve the displayed height for a direction change in the next effect.
        const height = element.getBoundingClientRect().height;
        cancelAnimation();
        element.style.height = `${height}px`;
      }
    };
  }, [panel, content, lastFocused, open, animateInitial, instant]);
}
