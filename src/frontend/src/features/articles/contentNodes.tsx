import { Node } from "@tiptap/core";
import type { JSONContent } from "@tiptap/core";
import { NodeViewWrapper, ReactNodeViewRenderer } from "@tiptap/react";
import type { NodeViewProps } from "@tiptap/react";
import type { Attachment } from "../../shared/api/types";
import { Attachments } from "../publications/Attachments";

function AttachmentView({ node }: NodeViewProps) {
  const descriptor = node.attrs.descriptor as Attachment | null;
  return <NodeViewWrapper contentEditable={false}>
    {descriptor ? <Attachments items={[descriptor]} /> : <span>Attachment unavailable</span>}
  </NodeViewWrapper>;
}

export const ArticleAttachment = Node.create({
  name: "attachment", group: "block", atom: true, draggable: true,
  addAttributes() { return { descriptor: { default: null } }; },
  parseHTML() { return []; },
  renderHTML() { return ["div", { "data-publication-attachment": "" }, "Attached content"]; },
  addNodeView() { return ReactNodeViewRenderer(AttachmentView); },
});

export const ArticleMention = Node.create({
  name: "mention", group: "inline", inline: true, atom: true,
  addAttributes() { return { user_id: { default: null } }; },
  parseHTML() { return []; },
  renderHTML({ node }) {
    return ["span", { class: "pill", title: String(node.attrs.user_id ?? "") }, "Account mention"];
  },
});

export const ArticleHashtag = Node.create({
  name: "hashtag", group: "inline", inline: true, atom: true,
  addAttributes() { return { tag: { default: null } }; },
  parseHTML() { return []; },
  renderHTML({ node }) { return ["span", { class: "pill" }, `#${String(node.attrs.tag ?? "")}`]; },
});

export function toEditorBody(node: JSONContent): JSONContent {
  return {
    ...node,
    ...(node.type === "attachment" ? { attrs: { descriptor: node.attrs } } : {}),
    ...(node.content ? { content: node.content.map(toEditorBody) } : {}),
  };
}

export function fromEditorBody(node: JSONContent): JSONContent {
  return {
    ...node,
    ...(node.type === "attachment" ? { attrs: node.attrs?.descriptor ?? {} } : {}),
    ...(node.content ? { content: node.content.map(fromEditorBody) } : {}),
  };
}
