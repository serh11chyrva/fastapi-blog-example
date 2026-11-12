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
