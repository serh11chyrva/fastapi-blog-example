import { useRef, useState } from "react";
import type { Attachment } from "../../shared/api/types";
import { Icon } from "../../shared/ui/Icon";

type Image = Extract<Attachment, { type: "image" }>;

export function MediaGallery({ images }: { images: Image[] }) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [selected, setSelected] = useState(0);
  const active = images[selected] ?? images[0];

  function show(index: number) {
    setSelected(index);
    dialog.current?.showModal();
  }

  function move(amount: number) {
    setSelected((index) => (index + amount + images.length) % images.length);
  }

  return <>
    <div className={`post-gallery gallery-${Math.min(images.length, 4)}`}>
      {images.slice(0, 4).map((image, index) => <button type="button" key={image.url}
        aria-label={image.alt || `View photo ${index + 1} of ${images.length}`} onClick={() => show(index)}>
        <img src={image.url} alt={image.alt} loading="lazy" />
        {index === 3 && images.length > 4 && <span className="gallery-extra">+{images.length - 4}</span>}
      </button>)}
    </div>
    <dialog className="photo-viewer" aria-label="Photo viewer" ref={dialog} onKeyDown={(event) => {
      if (event.key === "ArrowLeft") { event.preventDefault(); move(-1); }
      if (event.key === "ArrowRight") { event.preventDefault(); move(1); }
    }} onClick={(event) => { if (event.target === dialog.current) dialog.current?.close(); }}>
      <button type="button" className="icon-button viewer-close" aria-label="Close viewer" autoFocus
        onClick={() => dialog.current?.close()}><Icon name="close" width={24} height={24} /></button>
      <div className="viewer-stage">
        {images.length > 1 && <button type="button" className="icon-button" aria-label="Previous photo"
          onClick={() => move(-1)}><Icon name="left" width={26} height={26} /></button>}
        <figure><img src={active.url} alt={active.alt} loading="lazy" />
          <figcaption>{selected + 1} / {images.length}{active.alt && ` · ${active.alt}`}</figcaption>
        </figure>
        {images.length > 1 && <button type="button" className="icon-button" aria-label="Next photo"
          onClick={() => move(1)}><Icon name="right" width={26} height={26} /></button>}
      </div>
    </dialog>
  </>;
}
