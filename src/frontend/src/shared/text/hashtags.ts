export function hashtagHref(tag: string) {
  return `/search?${new URLSearchParams({ q: `#${tag}` })}`;
}

export function inlineTokens(text: string) {
  const pattern = /https?:\/\/[^\s<>]+|(?<![\p{L}\p{M}\p{N}_#])(?:@[a-z\d_]{3,24}|#[\p{L}\p{M}\p{N}_]+)/giu;
  return [...text.matchAll(pattern)].map((match) => ({
    start: match.index, end: match.index + match[0].length, value: match[0],
  }));
}

export function hashtagMatches(text: string) {
  return inlineTokens(text).filter(({ value }) => value.startsWith("#") && [...value.slice(1)].length <= 64);
}

export function inlineLinkTokens(text: string) {
  return inlineTokens(text).flatMap((token) => {
    const kind = token.value.startsWith("#") ? "hashtag" : token.value.startsWith("@") ? "mention" : "external";
    if (kind === "hashtag" && [...token.value.slice(1)].length > 64) return [];
    const value = kind === "external" ? token.value.replace(/[.,!?;:]+$/, "") : token.value;
    if (kind === "external") {
      try {
        const url = new URL(value);
        if (!["http:", "https:"].includes(url.protocol) || url.username || url.password) return [];
      } catch { return []; }
    }
    const href = kind === "hashtag" ? hashtagHref(value.slice(1)) : kind === "mention" ? `/${value}` : value;
    return [{ start: token.start, end: token.start + value.length, value, kind, href }];
  });
}
