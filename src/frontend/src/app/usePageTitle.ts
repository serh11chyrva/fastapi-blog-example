import { useLayoutEffect } from "react";

export const siteName = "FastAPI Blog Example";

export function usePageTitle(title: string | null) {
  useLayoutEffect(() => {
    if (title) document.title = `${title} — ${siteName}`;
  }, [title]);
}
