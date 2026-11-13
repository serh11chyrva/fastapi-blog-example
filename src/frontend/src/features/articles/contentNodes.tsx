import { Node } from "@tiptap/core";
import type { JSONContent } from "@tiptap/core";
import { NodeViewWrapper, ReactNodeViewRenderer } from "@tiptap/react";
import type { NodeViewProps } from "@tiptap/react";
import type { Attachment } from "../../shared/api/types";
import { Attachments } from "../publications/Attachments";
import { hashtagHref } from "../../shared/text/hashtags";
import { Mention } from "../../shared/text/Mention";

function AttachmentView({ node, editor }: NodeViewProps) {
  const descriptor = node.attrs.descriptor as Attachment | null;
  return <NodeViewWrapper contentEditable={false}>
    {descriptor ? <Attachments items={[descriptor]} editable={editor.isEditable} article /> : <span>Attachment unavailable</span>}
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
    return ["span", { class: "content-link mention", "data-mention": String(node.attrs.user_id ?? "") }, "Account mention"];
  },
  addNodeView() { return ReactNodeViewRenderer(MentionView); },
});

function MentionView({ node, editor }: NodeViewProps) {
  return <NodeViewWrapper as="span" contentEditable={false}>
    <Mention userId={String(node.attrs.user_id ?? "")} editable={editor.isEditable} />
  </NodeViewWrapper>;
}

export const ArticleHashtag = Node.create<{ editable: boolean }>({
  name: "hashtag", group: "inline", inline: true, atom: true,
  addOptions() { return { editable: true }; },
  addAttributes() { return { tag: { default: null } }; },
  parseHTML() { return []; },
  renderHTML({ node }) {
    const tag = String(node.attrs.tag ?? "");
    return this.options.editable ? ["span", { class: "content-link hashtag" }, `#${tag}`]
      : ["a", { class: "content-link hashtag", href: hashtagHref(tag), "data-content-internal": "" }, `#${tag}`];
  },
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
