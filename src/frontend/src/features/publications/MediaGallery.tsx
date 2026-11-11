import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import type { Attachment } from "../../shared/api/types";
import { Icon } from "../../shared/ui/Icon";

type Image = Extract<Attachment, { type: "image" }>;

export function MediaGallery({ images }: { images: Image[] }) {
  const track = useRef<HTMLDivElement>(null);
  const dialog = useRef<HTMLDialogElement>(null);
  const opener = useRef<HTMLElement | null>(null);
  const previousOverflow = useRef<string | null>(null);
  const [selected, setSelected] = useState(0);
  const [slide, setSlide] = useState(0);
  const [failed, setFailed] = useState<string[]>([]);
  const [edges, setEdges] = useState({ previous: false, next: false });
  const [ratios, setRatios] = useState<Record<string, number>>({});
  const [viewport, setViewport] = useState({ width: 0, height: window.innerHeight });
  const selectedRef = useRef(0);
  const slideRef = useRef(0);
  const count = images.length;
  const active = images[Math.min(selected, count - 1)];
  const signature = images.map((image) => image.url).join("|");
  const reference = images.find((image) => !failed.includes(image.url));
  const firstRatio = reference ? ratios[reference.url] ?? 1.5 : 1.5;
  const height = Math.min(viewport.width * .84 / firstRatio, viewport.height * .5);

  const updateEdges = useCallback(() => {
    const element = track.current;
    if (!element) return;
    const previous = element.scrollLeft > 1;
    const next = element.scrollLeft < element.scrollWidth - element.clientWidth - 1;
    setEdges((value) => value.previous === previous && value.next === next ? value : { previous, next });
  }, []);

  const go = useCallback((index: number, smooth = true) => {
    const element = track.current;
    if (!element || !count) return;
    const next = Math.max(0, Math.min(index, count - 1));
    const child = element.children[next] as HTMLElement | undefined;
    if (child) element.scrollTo({ left: Math.min(child.offsetLeft, element.scrollWidth - element.clientWidth),
      behavior: smooth && !window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "smooth" : "instant" });
    slideRef.current = next; setSlide(next);
  }, [count]);

  const restore = useCallback(() => {
    if (previousOverflow.current !== null) {
      document.body.style.overflow = previousOverflow.current;
      previousOverflow.current = null;
    }
  }, []);

  useEffect(() => {
    selectedRef.current = Math.min(selectedRef.current, Math.max(0, count - 1));
    setSelected(selectedRef.current);
    slideRef.current = Math.min(slideRef.current, Math.max(0, count - 1));
    if (!count) { dialog.current?.close(); restore(); }
    const element = track.current;
    const resize = () => {
      const width = element?.clientWidth ?? 0;
      const viewportHeight = window.visualViewport?.height ?? window.innerHeight;
      setViewport((value) => value.width === width && value.height === viewportHeight
        ? value : { width, height: viewportHeight });
      go(slideRef.current, false);
      updateEdges();
    };
    const observer = new ResizeObserver(resize);
    if (element) observer.observe(element);
    window.addEventListener("resize", resize);
    window.visualViewport?.addEventListener("resize", resize);
    resize();
    return () => {
      observer.disconnect();
      window.removeEventListener("resize", resize);
      window.visualViewport?.removeEventListener("resize", resize);
    };
  }, [signature, count, go, restore, updateEdges]);
  useEffect(() => () => restore(), [restore]);
  useLayoutEffect(() => {
    go(slideRef.current, false);
    updateEdges();
  }, [height, ratios, signature, go, updateEdges]);

  function show(index: number, trigger: HTMLElement) {
    selectedRef.current = index; setSelected(index); opener.current = trigger;
    if (!dialog.current?.open) {
      previousOverflow.current = document.body.style.overflow;
      dialog.current?.showModal(); document.body.style.overflow = "hidden";
    }
  }
  function move(amount: number) {
    selectedRef.current = Math.max(0, Math.min(selectedRef.current + amount, count - 1));
    setSelected(selectedRef.current);
  }
  function imageError(url: string) { setFailed((items) => items.includes(url) ? items : [...items, url]); }
  function imageLoaded(url: string, element: HTMLImageElement) {
    if (!element.naturalWidth || !element.naturalHeight) return;
    const ratio = element.naturalWidth / element.naturalHeight;
    setRatios((value) => value[url] === ratio ? value : { ...value, [url]: ratio });
  }

  if (!active) return null;
  return <div className="photo-carousel" data-can-prev={edges.previous} data-can-next={edges.next}>
    <div className="carousel-viewport">
      <div ref={track} className={`carousel-track ${count === 1 ? "single-image" : ""}`} tabIndex={0}
        role="region" aria-roledescription="carousel" aria-label={`Photo gallery, ${count} images`}
        onKeyDown={(event) => {
          if (event.target !== event.currentTarget) return;
          if (event.key === "ArrowLeft" || event.key === "ArrowRight") {
            event.preventDefault(); go(slide + (event.key === "ArrowRight" ? 1 : -1));
          }
        }} onScroll={() => {
          updateEdges();
          const element = track.current;
          if (!element) return;
          let nearest = 0;
          Array.from(element.children).forEach((child, index) => {
            const offset = Math.min((child as HTMLElement).offsetLeft, element.scrollWidth - element.clientWidth);
            const best = Math.min((element.children[nearest] as HTMLElement).offsetLeft, element.scrollWidth - element.clientWidth);
            if (Math.abs(offset - element.scrollLeft) < Math.abs(best - element.scrollLeft)) nearest = index;
          });
          const end = element.scrollWidth - element.clientWidth;
          if (end > 1 && element.scrollLeft >= end - 1) nearest = count - 1;
          slideRef.current = nearest; setSlide(nearest);
        }}>
        {images.map((image, index) => <button key={image.url} type="button" className="carousel-slide"
          style={count > 1 && height > 0 ? {
            height, flexBasis: Math.min(height * (ratios[image.url] ?? 1.5), viewport.width),
          } : undefined}
          aria-label={`View photo ${index + 1} of ${count}${image.alt ? `: ${image.alt}` : ""}`}
          onClick={(event) => show(index, event.currentTarget)}>
          {failed.includes(image.url) ? <span className="image-unavailable">Image unavailable</span>
            : <img src={image.url} alt={image.alt} loading="lazy"
                onLoad={(event) => imageLoaded(image.url, event.currentTarget)} onError={() => imageError(image.url)} />}
        </button>)}
      </div>
      {count > 1 && <>
        <button type="button" className="carousel-circle carousel-prev" aria-label="Previous image" disabled={!edges.previous} onClick={() => go(slide - 1)}><Icon name="left" /></button>
        <button type="button" className="carousel-circle carousel-next" aria-label="Next image" disabled={!edges.next} onClick={() => go(slide + 1)}><Icon name="right" /></button>
      </>}
    </div>
    {count > 1 && <p className="gallery-count" aria-live="polite">{slide + 1} / {count}</p>}
    <dialog ref={dialog} className="photo-viewer carousel-viewer" aria-label={`Photo ${selected + 1} of ${count}`}
      onClose={() => { restore(); go(selectedRef.current, false); opener.current?.focus({ preventScroll: true }); }}
      onKeyDown={(event) => {
        if (event.key === "ArrowLeft" || event.key === "ArrowRight") { event.preventDefault(); move(event.key === "ArrowRight" ? 1 : -1); }
      }} onClick={(event) => {
        if (event.target !== dialog.current) return;
        const box = event.currentTarget.getBoundingClientRect();
        if (event.clientX < box.left || event.clientX > box.right || event.clientY < box.top || event.clientY > box.bottom) dialog.current?.close();
      }}>
      <button type="button" className="viewer-close" aria-label="Close photo viewer" autoFocus onClick={() => dialog.current?.close()}><Icon name="close" /></button>
      <div className="carousel-viewer-stage">
        {failed.includes(active.url) ? <p className="image-unavailable">Image unavailable</p>
          : <img className="viewer-image" src={active.url} alt={active.alt} onClick={() => dialog.current?.close()} onError={() => imageError(active.url)} />}
        {count > 1 && <>
          <button type="button" className="viewer-nav viewer-prev" aria-label="Previous photo" disabled={selected === 0} onClick={() => move(-1)}><Icon name="left" /></button>
          <button type="button" className="viewer-nav viewer-next" aria-label="Next photo" disabled={selected === count - 1} onClick={() => move(1)}><Icon name="right" /></button>
        </>}
        <span className="sr-only" aria-live="polite">Photo {selected + 1} of {count}. {active.alt}</span>
      </div>
    </dialog>
  </div>;
}
