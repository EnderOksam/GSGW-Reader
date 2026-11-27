import alttextData from "$lib/dodalttext.json";

// Keep original text per node so toggling never rebuilds the chapter's markup.
const originalText = new WeakMap<Text, string>();

export function applyDebutAltText(article: HTMLElement, selections: Record<string, string>) {
  const replacements = new Map<string, string>();
  for (const variant of alttextData.variants) {
    const option = selections[variant.name];
    if (variant.options.includes(option)) {
      for (const search of variant.searches) {
        replacements.set(search.toLowerCase(), option);
      }
    }
  }

  const patterns = [...replacements.keys()].map(search =>
    `\\b${search.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}\\b`
  );
  const regex = patterns.length ? new RegExp(patterns.join("|"), "gi") : null;
  const walker = document.createTreeWalker(article, NodeFilter.SHOW_TEXT);
  let node: Text | null;
  while ((node = walker.nextNode() as Text | null)) {
    const original = originalText.get(node) ?? node.data;
    if (regex) {
      originalText.set(node, original);
      node.data = original.replace(regex, match => {
        const replacement = replacements.get(match.toLowerCase())!;
        if (match === match.toUpperCase()) return replacement.toUpperCase();
        if (match === match.toLowerCase()) return replacement.toLowerCase();
        return replacement;
      });
    } else if (originalText.has(node)) {
      node.data = original;
    }
  }
}
