let pristineHTML: string | null = null;

export function storePristine(article: HTMLElement) {
  pristineHTML = article.innerHTML;
}

export interface AltTextVariant {
  name: string;
  description: string;
  searches: string[];
  options: string[];
}

export function applyAltText(article: HTMLElement, pairs: [string, string][]) {
  if (!pristineHTML) {
    storePristine(article);
  }

  if (pristineHTML) {
    article.innerHTML = pristineHTML;
  }

  const escaped = pairs.map(([s]) => {
    const e = s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    const left = /^\w/.test(s) ? "\\b" : "";
    const right = /\w$/.test(s) ? "\\b" : "";
    return `${left}${e}${right}`;
  });
  const combined = escaped.join("|");
  if (!combined) return;

  const regex = new RegExp(combined, "gi");

  const replaceMap = new Map<string, string>();
  for (const [search, replace] of pairs) {
    replaceMap.set(search.toLowerCase(), replace);
  }

  const walker = document.createTreeWalker(article, NodeFilter.SHOW_TEXT, null);
  const textNodes: Text[] = [];
  let node: Text | null;
  while ((node = walker.nextNode() as Text | null)) {
    textNodes.push(node);
  }

  for (const textNode of textNodes) {
    const original = textNode.nodeValue || "";

    regex.lastIndex = 0;
    if (!regex.test(original)) continue;

    regex.lastIndex = 0;
    const replaced = original.replace(regex, (match) => {
      const key = match.toLowerCase();
      const repl = replaceMap.get(key);
      if (!repl) return match;

      if (match === match.toUpperCase() && match.length > 1) {
        return repl.toUpperCase();
      }
      if (match[0] === match[0].toUpperCase()) {
        return repl.charAt(0).toUpperCase() + repl.slice(1).toLowerCase();
      }
      return repl.toLowerCase();
    });

    textNode.nodeValue = replaced;
  }
}

export function clearAltText(article: HTMLElement) {
  if (pristineHTML) {
    article.innerHTML = pristineHTML;
  }
}
