import { PublicationComposer } from "../publications/PublicationComposer";

export function PostComposer({ onPosted }: { onPosted: () => void }) {
  return <PublicationComposer onSaved={onPosted} />;
}
