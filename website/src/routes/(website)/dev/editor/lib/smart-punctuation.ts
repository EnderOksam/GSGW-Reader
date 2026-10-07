/** Display-only substitutions. Offsets always refer to the untouched Markdown. */
export interface Punctuation { from: number; to: number; text: string }

export function smartPunctuation(source: string): Punctuation[] {
  const protectedChars = new Uint8Array(source.length);
  // Keep Markdown syntax, code, escapes, destinations, metadata and HTML literal.
  const literal = /^(?: {4}|\t).*$/gm;
  const patterns = [literal, /^---[ \t]*\n[\s\S]*?\n(?:---|\.\.\.)[ \t]*(?=\n|$)/g,
    /^ {0,3}(`{3,}|~{3,})[^\n]*\n[\s\S]*?(?:^ {0,3}\1[^\n]*(?=\n|$)|(?![\s\S]))/gm,
    /(`+)([\s\S]*?)\1/g, /\\[\s\S]/g, /<(pre|code|script|style)\b[^>]*>[\s\S]*?<\/\1\s*>|<!--[\s\S]*?-->|<[^>]*>/gi,
    /\]\([^\n]*\)/g, /^ {0,3}\[[^\]\n]+\]:[^\n]*$/gm,
    /^ {0,3}(?:-[ \t]*){3,}$/gm, /^ {0,3}\|?[ \t]*:?-{3,}:?(?:[ \t]*\|[ \t]*:?-{3,}:?)*[ \t]*\|?[ \t]*$/gm];
  for (const pattern of patterns) for (const m of source.matchAll(pattern)) {
    protectedChars.fill(1, m.index, m.index + m[0].length);
  }
  const result: Punctuation[] = [];
  const word = (s: string) => /[\p{L}\p{N}]/u.test(s);
  for (let i = 0; i < source.length; i++) {
    if (protectedChars[i]) continue;
    const c = source[i];
    if (c === '-' && source[i + 1] === '-' && !protectedChars[i + 1]) {
      const n = source[i + 2] === '-' && !protectedChars[i + 2] ? 3 : 2;
      result.push({ from: i, to: i + n, text: n === 3 ? '—' : '–' });
      i += n - 1;
    } else if (c === '"' || c === "'") {
      const before = source.slice(0, i).replace(/[*_]+$/, '').slice(-1);
      const after = source[i + 1] ?? '';
      const apostrophe = c === "'" && word(before);
      const opening = !apostrophe && (!before || /[\s([{“‘—–]/u.test(before)) && !!after && !/\s/.test(after);
      result.push({ from: i, to: i + 1, text: c === '"' ? (opening ? '“' : '”') : (opening ? '‘' : '’') });
    }
  }
  return result;
}

/** A mirror keeps native selection, clipboard, undo and IME on the raw textarea. */
export function punctuationDisplay(el: HTMLTextAreaElement, source: string) {
  const mirror = document.createElement('div');
  mirror.className = 'punctuation-mirror';
  mirror.setAttribute('aria-hidden', 'true');
  el.parentElement!.append(mirror);
  const observer = new ResizeObserver(sync);
  observer.observe(el);
  el.classList.add('punctuation-input');
  function sync() {
    const style = getComputedStyle(el);
    for (const key of ['font', 'lineHeight', 'letterSpacing', 'padding', 'borderWidth', 'boxSizing', 'tabSize', 'textIndent'] as const) mirror.style[key] = style[key];
    mirror.style.width = `${el.clientWidth + parseFloat(style.borderLeftWidth) + parseFloat(style.borderRightWidth)}px`;
    mirror.style.height = `${el.offsetHeight}px`;
    mirror.scrollTop = el.scrollTop;
    mirror.scrollLeft = el.scrollLeft;
  }
  function render(value: string) {
    mirror.replaceChildren();
    let last = 0;
    for (const item of smartPunctuation(value)) {
      mirror.append(document.createTextNode(value.slice(last, item.from)));
      const span = document.createElement('span');
      span.className = 'punctuation-source';
      span.textContent = value.slice(item.from, item.to);
      const glyph = document.createElement('span');
      glyph.className = 'punctuation-glyph';
      glyph.textContent = item.text;
      span.append(glyph);
      mirror.append(span);
      last = item.to;
    }
    mirror.append(document.createTextNode(value.slice(last) + '\n'));
    sync();
  }
  function compositionStart() { el.classList.remove('punctuation-input'); mirror.hidden = true; }
  function compositionEnd() { el.classList.add('punctuation-input'); mirror.hidden = false; render(el.value); }
  el.addEventListener('scroll', sync);
  el.addEventListener('compositionstart', compositionStart);
  el.addEventListener('compositionend', compositionEnd);
  render(source);
  return { update: render, destroy() {
    observer.disconnect(); mirror.remove(); el.classList.remove('punctuation-input');
    el.removeEventListener('scroll', sync);
    el.removeEventListener('compositionstart', compositionStart);
    el.removeEventListener('compositionend', compositionEnd);
  } };
}
