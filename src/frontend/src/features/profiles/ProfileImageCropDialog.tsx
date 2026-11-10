import { useEffect, useId, useRef, useState } from "react";
import { errorMessage } from "../../shared/api/client";
import { Icon } from "../../shared/ui/Icon";

export type ProfileImageKind = "avatar" | "banner";

type Point = { x: number; y: number };
type Size = { width: number; height: number };

function clampPosition(value: number) {
  return Math.max(0, Math.min(1, value));
}

export function ProfileImageCropDialog({ file, kind, onApply, onCancel }: {
  file: File;
  kind: ProfileImageKind;
  onApply: (file: File) => void;
  onCancel: () => void;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const image = useRef<HTMLImageElement>(null);
  const titleId = useId();
  const drag = useRef<{ pointerId: number; start: Point; position: Point; scale: Point } | null>(null);
  const [source, setSource] = useState("");
  const [size, setSize] = useState<Size>();
  const [zoom, setZoom] = useState(1);
  const [position, setPosition] = useState<Point>({ x: 0.5, y: 0.5 });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const ratio = kind === "avatar" ? 1 : 4;
  const width = size ? Math.min(size.width, size.height * ratio) / zoom : 0;
  const height = width / ratio;
  const availableX = size ? Math.max(0, size.width - width) : 0;
  const availableY = size ? Math.max(0, size.height - height) : 0;
  const x = availableX * position.x;
  const y = availableY * position.y;

  useEffect(() => {
    const url = URL.createObjectURL(file);
    setSource(url);
    if (!dialog.current?.open) dialog.current?.showModal();
    return () => URL.revokeObjectURL(url);
  }, [file]);

  async function applyCrop() {
    if (!image.current || !width || busy) return;
    setBusy(true);
    setError("");
    try {
      const canvas = document.createElement("canvas");
      canvas.height = Math.max(1, Math.min(kind === "avatar" ? 512 : 400, Math.floor(height)));
      canvas.width = canvas.height * ratio;
      const context = canvas.getContext("2d");
      if (!context) throw new Error("Your browser could not crop this image.");

      context.drawImage(image.current, x, y, width, height, 0, 0, canvas.width, canvas.height);
      const blob = await new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, file.type, 0.92));
      if (!blob) throw new Error("Could not prepare the cropped image.");
      if (!dialog.current?.open) return;

      const extension = blob.type === "image/jpeg" ? "jpg" : blob.type.split("/")[1];
      dialog.current.close();
      onApply(new File([blob], `${kind}.${extension}`, { type: blob.type }));
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusy(false);
    }
  }

  return <dialog ref={dialog} className="design-dialog profile-crop-dialog" aria-labelledby={titleId} onClose={onCancel}>
    <div className="dialog-heading">
      <h2 id={titleId}>Crop {kind}</h2>
      <button type="button" className="icon-button" aria-label="Close crop editor" onClick={() => dialog.current?.close()}>
        <Icon name="close" />
      </button>
    </div>
    <div className="dialog-body">
      <p>Drag the image or use the sliders to adjust the crop.</p>
      <div className="profile-crop-preview" data-avatar={kind === "avatar" || undefined} style={{ aspectRatio: ratio }}
        onPointerDown={(event) => {
          if (!size || busy || event.button !== 0 || !event.isPrimary) return;
          const preview = event.currentTarget.getBoundingClientRect();
          event.currentTarget.setPointerCapture(event.pointerId);
          drag.current = {
            pointerId: event.pointerId,
            start: { x: event.clientX, y: event.clientY },
            position,
            scale: {
              x: availableX > 0 ? width / (preview.width * availableX) : 0,
              y: availableY > 0 ? height / (preview.height * availableY) : 0,
            },
          };
        }}
        onPointerMove={(event) => {
          const gesture = drag.current;
          if (!gesture || gesture.pointerId !== event.pointerId) return;
          setPosition({
            x: clampPosition(gesture.position.x - (event.clientX - gesture.start.x) * gesture.scale.x),
            y: clampPosition(gesture.position.y - (event.clientY - gesture.start.y) * gesture.scale.y),
          });
        }}
        onLostPointerCapture={() => { drag.current = null; }}>
        {source && <img ref={image} src={source} alt={`${kind} crop preview`} draggable={false}
          onLoad={(event) => setSize({ width: event.currentTarget.naturalWidth, height: event.currentTarget.naturalHeight })}
          onError={() => { setSize(undefined); setError("Could not open this image. Choose another file."); }}
          style={size ? {
            width: `${size.width / width * 100}%`, height: `${size.height / height * 100}%`,
            left: `${-x / width * 100}%`, top: `${-y / height * 100}%`,
          } : { visibility: "hidden" }} />}
      </div>
      <fieldset className="profile-crop-sliders" disabled={!size || busy}>
        <label>Zoom<input type="range" min={1} max={4} step={0.01} value={zoom}
          onChange={(event) => setZoom(event.target.valueAsNumber)} /></label>
        <label>Horizontal<input type="range" min={0} max={1} step={0.01} value={position.x} disabled={!availableX}
          onChange={(event) => setPosition((current) => ({ ...current, x: event.target.valueAsNumber }))} /></label>
        <label>Vertical<input type="range" min={0} max={1} step={0.01} value={position.y} disabled={!availableY}
          onChange={(event) => setPosition((current) => ({ ...current, y: event.target.valueAsNumber }))} /></label>
      </fieldset>
      {error && <p className="notice-error" role="alert">{error}</p>}
      <div className="profile-crop-actions">
        <button type="button" className="button-secondary" onClick={() => dialog.current?.close()}>Cancel</button>
        <button type="button" className="button-primary" disabled={!size || busy} onClick={() => void applyCrop()}>
          {busy ? "Preparing…" : "Crop and upload"}
        </button>
      </div>
    </div>
  </dialog>;
}
