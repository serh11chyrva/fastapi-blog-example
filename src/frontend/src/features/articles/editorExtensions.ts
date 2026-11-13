import { Extension, Mark } from "@tiptap/core";
import StarterKit from "@tiptap/starter-kit";
import LinkExtension from "@tiptap/extension-link";
import Superscript from "@tiptap/extension-superscript";
import { EditorialCode, EditorialQuote } from "./EditorialBlocks";
import { ArticleAttachment, ArticleHashtag, ArticleMention } from "./contentNodes";
import { ArticleImage } from "./ArticleImage";
import { ArticleTextLinks } from "./hashtagExtension";
import { ArticleSectionAnchors } from "./ArticleSections";
import { ArticleEquation } from "./ArticleEquation";

const LegacyStrike = Mark.create({
  name: "strike",
  inclusive: false,
  parseHTML() { return []; },
  renderHTML() { return ["s", 0]; },
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
    ];
  },
});

export function createEditorExtensions(editable = true, navigate?: (href: string) => void) {
  return [
    StarterKit.configure({ heading: { levels: [1, 2, 3] }, strike: false, link: false, trailingNode: false, blockquote: false, codeBlock: false }),
    LegacyStrike,
    Superscript,
    ArticleFormatting,
    ArticleSectionAnchors,
    EditorialQuote,
    EditorialCode,
    ArticleEquation,
    ArticleImage,
    ArticleAttachment,
    ArticleMention,
    ArticleHashtag.configure({ editable }),
    ArticleTextLinks.configure({ navigate }),
    LinkExtension.configure({ openOnClick: !editable, HTMLAttributes: {
      class: "content-link external-link", rel: "noopener noreferrer nofollow", target: "_blank",
    } }),
  ];
}
