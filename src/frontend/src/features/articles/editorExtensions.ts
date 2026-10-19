import { Node } from "@tiptap/core";
import StarterKit from "@tiptap/starter-kit";
import LinkExtension from "@tiptap/extension-link";
import { ArticleAttachment, ArticleHashtag, ArticleMention } from "./contentNodes";
const ArticleImage = Node.create({
  name: "image", group: "block", atom: true, draggable: true,
  addAttributes() { return { src: { default: null }, alt: { default: null }, title: { default: null } }; },
  parseHTML() { return [{ tag: "img[src]" }]; },
  renderHTML({ HTMLAttributes }) { return ["img", { ...HTMLAttributes, loading: "lazy" }]; },
});
export function createEditorExtensions(editable = true) {
  return [
    StarterKit.configure({ heading: { levels: [1, 2, 3] }, link: false, underline: false, trailingNode: false }),
    ArticleImage,
    ArticleAttachment,
    ArticleMention,
    ArticleHashtag,
    LinkExtension.configure({ openOnClick: !editable, HTMLAttributes: { rel: "noopener noreferrer nofollow", target: "_blank" } }),
  ];
}
