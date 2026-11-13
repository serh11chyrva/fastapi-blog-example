import { Extension } from "@tiptap/core";
import { Plugin } from "@tiptap/pm/state";
import { Decoration, DecorationSet } from "@tiptap/pm/view";
import { inlineLinkTokens } from "../../shared/text/hashtags";

export const ArticleTextLinks = Extension.create<{
  navigate?: (href: string) => void;
}>({
  name: "articleTextLinks",
  addOptions() { return {}; },
  addProseMirrorPlugins() {
    const extension = this;
    return [new Plugin({
      props: {
        decorations(state) {
          const decorations: Decoration[] = [];
          state.doc.descendants((node, position) => {
            if (!["paragraph", "heading"].includes(node.type.name)) return;
            let text = "";
            let start = position + 1;
            const flush = () => {
              for (const token of inlineLinkTokens(text)) {
                const editable = extension.editor.isEditable;
                const external = token.kind === "external";
                decorations.push(Decoration.inline(start + token.start, start + token.end, {
                  class: `content-link ${external ? "external-link" : token.kind}`, nodeName: editable ? "span" : "a",
                  ...(!editable ? { href: token.href, ...(external
                    ? { target: "_blank", rel: "noopener noreferrer nofollow" }
                    : { "data-content-internal": "" }) } : {}),
                }));
              }
              text = "";
            };
            node.forEach((child, offset) => {
              if (child.isText && !child.marks.some((mark) => ["code", "link"].includes(mark.type.name))) {
                if (!text) start = position + 1 + offset;
                text += child.text ?? "";
              } else flush();
            });
            flush();
            return false;
          });
          return DecorationSet.create(state.doc, decorations);
        },
        handleClick(view, _position, event) {
          const anchor = event.target instanceof Element ? event.target.closest<HTMLAnchorElement>("a.content-link") : null;
          if (!anchor) return false;
          if (view.editable) { event.preventDefault(); return true; }
          if (event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey
            || !anchor.hasAttribute("data-content-internal") || !extension.options.navigate) return false;
          event.preventDefault();
          extension.options.navigate(anchor.getAttribute("href") ?? "/");
          return true;
        },
      },
    })];
  },
});
