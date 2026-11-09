import { Extension, Node } from "@tiptap/core";
import StarterKit from "@tiptap/starter-kit";
import LinkExtension from "@tiptap/extension-link";
import { ArticleAttachment, ArticleHashtag, ArticleMention } from "./contentNodes";
const ArticleImage = Node.create({
  name: "image", group: "block", atom: true, draggable: true,
  addAttributes() { return { src: { default: null }, alt: { default: null }, title: { default: null } }; },
  parseHTML() { return [{ tag: "img[src]" }]; },
  renderHTML({ HTMLAttributes }) { return ["img", { ...HTMLAttributes, loading: "lazy" }]; },
});
const ArticleFormatting = Extension.create({
  name: "articleFormatting",
  addGlobalAttributes() {
    return [
      {
        types: ["paragraph", "heading"],
        attributes: {
          textAlign: {
            default: null,
            parseHTML: (element) => element.style.textAlign || null,
            renderHTML: ({ textAlign }) => ["left", "center", "right", "justify"].includes(textAlign)
              ? { style: `text-align: ${textAlign}` } : {},
          },
        },
      },
      {
        types: ["heading"],
        attributes: {
          sectionId: {
            default: null,
            renderHTML: ({ sectionId }) => typeof sectionId === "string" && /^section-\d+$/.test(sectionId)
              ? { id: sectionId } : {},
          },
        },
      },
      {
        types: ["blockquote"],
        attributes: {
          citation: {
            default: null,
            parseHTML: (element) => element.dataset.citation ?? null,
            renderHTML: ({ citation }) => typeof citation === "string" && citation ? { "data-citation": citation } : {},
          },
        },
      },
    ];
  },
});

export function createEditorExtensions(editable = true) {
  return [
    StarterKit.configure({ heading: { levels: [1, 2, 3] }, link: false, trailingNode: false }),
    ArticleFormatting,
    ArticleImage,
    ArticleAttachment,
    ArticleMention,
    ArticleHashtag,
    LinkExtension.configure({ openOnClick: !editable, HTMLAttributes: { rel: "noopener noreferrer nofollow", target: "_blank" } }),
  ];
}
