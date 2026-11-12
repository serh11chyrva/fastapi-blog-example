import { Extension } from "@tiptap/core";
import { Plugin } from "@tiptap/pm/state";
import { Decoration, DecorationSet } from "@tiptap/pm/view";
import { hashtagHref, hashtagMatches } from "../../shared/text/hashtags";

export const ArticleTextHashtags = Extension.create<{
  navigate?: (href: string) => void;
}>({
  name: "articleTextHashtags",
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
              for (const match of hashtagMatches(text)) {
                const tag = match.value.slice(1);
                const editable = extension.editor.isEditable;
                decorations.push(Decoration.inline(start + match.start, start + match.end, {
                  class: "hashtag", nodeName: editable ? "span" : "a",
                  ...(!editable ? { href: hashtagHref(tag), "data-search-hashtag": tag } : {}),
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
          if (view.editable || event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey)
            return false;
          const anchor = event.target instanceof Element ? event.target.closest<HTMLAnchorElement>("a[data-search-hashtag]") : null;
          if (!anchor || !extension.options.navigate) return false;
          event.preventDefault();
          extension.options.navigate(anchor.getAttribute("href") ?? "/search");
          return true;
        },
      },
    })];
  },
});
