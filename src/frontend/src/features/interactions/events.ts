import type { InteractionAction, PublicationKind } from "../../shared/api/types";

export const publicationEvent = "publication-created";
export const interactionEvent = "publication-interactions-changed";
export type InteractionChange = {
  kind: PublicationKind;
  id: string;
  action?: InteractionAction;
  enabled?: boolean;
};

export function notifyInteractionChange(change: InteractionChange) {
  window.dispatchEvent(new CustomEvent<InteractionChange>(interactionEvent, { detail: change }));
}

export function publicationPath(kind: PublicationKind, id: string) {
  return `/${kind === "micro_post" ? "posts" : "articles"}/${encodeURIComponent(id)}`;
}
