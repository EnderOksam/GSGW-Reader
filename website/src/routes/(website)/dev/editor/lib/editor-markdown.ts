import { replaceTwitterUrls } from "$lib/reader/twitter-embeds";
import { REPO, BRANCH } from "./github-api";

function makeWindow(cls: string, inner: string, extra?: string): string {
  const cl = extra ? `${cls} ${extra}` : cls;
  return `\n<div class="${cl}">\n\n${inner}\n\n</div>\n`;
}

function toParagraphs(inner: string): string {
  return inner
    .split(/\n+/)
    .filter(l => l.trim() !== "")
    .map(l => `<p>${l}</p>`)
    .join("\n");
}

function escapeHtml(text: string): string {
  return text.split(/(<[^>]*>)/).map((part, i) => {
    if (i % 2 === 1) return part;
    return part.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }).join("");
}

function fmtInline(text: string): string {
  return text
    .replace(/\*\*\*(.+?)\*\*\*/g, "<strong><em>$1</em></strong>")
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.+?)\*/g, "<em>$1</em>");
}

function imgInline(text: string, book: string): string {
  return text.replace(/!\[([^\]]*)\]\(([^)\s]+)(?:\s+"[^"]*")?\)/g, (_m: string, alt: string, href: string) => {
    const src = href.startsWith("http") || href.startsWith("/")
      ? href
      : `https://raw.githubusercontent.com/${REPO}/${BRANCH}/images/${book === "debut" ? "dod" : "gsgw"}/illustrations/${href}`;
    return `<img src="${src}" alt="${alt.replace(/"/g, "&quot;")}" loading="lazy" onerror="this.style.display='none'">`;
  });
}

const simpleInlineTags: [RegExp, string][] = [
  [/(?<!\\)_(.*?)(?<!\\)_/gs, '<span class="underline">$1</span>'],

  [/@ll@(.*?)@ll@/gs, '<span class="mono mono-left">$1</span>'],
  [/@cc@(.*?)@cc@/gs, '<span class="mono mono-center">$1</span>'],
  [/@rr@(.*?)@rr@/gs, '<span class="mono mono-right">$1</span>'],
  [/@l@(.*?)@l@/gs, '<span class="align-left">$1</span>'],
  [/@c@(.*?)@c@/gs, '<span class="align-center">$1</span>'],
  [/@r@(.*?)@r@/gs, '<span class="align-right">$1</span>'],
  [/#\*(.*?)\*#/gs, '<span class="text-large">$1</span>'],
  [/#><(.*?)><#/gs, '<span class="text-large-centered">$1</span>'],
  [/#r(.*?)r#/gs, '<span class="text-red">$1</span>'],
  [/#b(.*?)b#/gs, '<span class="text-blue">$1</span>'],
  [/#y(.*?)y#/gs, '<span class="text-yellow">$1</span>'],
  [/#p(.*?)p#/gs, '<span class="text-magenta">$1</span>'],
  [/#g(.*?)g#/gs, '<span class="text-green">$1</span>'],
  [/#o(.*?)o#/gs, '<span class="text-orange">$1</span>'],
  [/#lp(.*?)lp#/gs, '<span class="text-light-purple">$1</span>'],
  [/#cy(.*?)cy#/gs, '<span class="text-cyan">$1</span>'],
  [/#d(.*?)d#/gs, '<span class="text-black">$1</span>'],
  [/#f#(.*?)#f#/gs, '<span class="text-faded">$1</span>'],
  [/(?<!\\)-#\s*(.+?)\s*#-(?!\\)/gs, '<span class="text-sub">$1</span>'],
  [/#f>#(.*?)#f>#/gs, '<span class="text-fade-right">$1</span>'],
  [/#f<#(.*?)#f<#/gs, '<span class="text-fade-left">$1</span>'],
  [/;r(.*?)r;/gs, '<span class="hl-red">$1</span>'],
  [/;b(.*?)b;/gs, '<span class="hl-blue">$1</span>'],
  [/;y(.*?)y;/gs, '<span class="hl-yellow">$1</span>'],
  [/;p(.*?)p;/gs, '<span class="hl-magenta">$1</span>'],
  [/;g(.*?)g;/gs, '<span class="hl-green">$1</span>'],
  [/;o(.*?)o;/gs, '<span class="hl-orange">$1</span>'],
  [/\$\$(.*?)\$\$/gs, '<span class="handwritten">$1</span>'],
  [/\$lat(.*?)lat\$/gs, '<span class="lato">$1</span>'],
  [/\$fox(.*?)fox\$/gs, '<span class="fox">$1</span>'],
  [/\$Eb(.*?)Eb\$/gs, '<span class="eb-garamond">$1</span>'],
  [/\$h(?!x)(.*?)h\$/gs, '<span class="paulo-bittencourt">$1</span>'],
  [/\$nbg(.*?)nbg\$/gs, '<span class="nanum-barun-gothic">$1</span>'],
  [/\$tf(.*?)tf\$/gs, '<span class="chungju-kimsaeng">$1</span>'],
  [/\$vcr(.*?)vcr\$/gs, '<span class="vcr-osd-mono">$1</span>'],
  [/\$Bh(.*?)Bh\$/gs, '<span class="braun-handwriting">$1</span>'],
  [/\$c(.*?)c\$/gs, '<span class="contaminated">$1</span>'],
  [/\$wo(.*?)wo\$/gs, '<span class="outline-white">$1</span>'],
  [/\$bo(.*?)bo\$/gs, '<span class="outline-black">$1</span>'],
];

function renderFootnoteText(text: string): string {
  let s = text
    .replace(/\*\*\*(.+?)\*\*\*/g, "<strong><em>$1</em></strong>")
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.+?)\*/g, "<em>$1</em>");

  const links: Record<string, string> = {};
  let linkId = 0;
  s = s.replace(/\[([^\]]+)\]\(([^)]+)\)/g, (_: string, label: string, url: string) => {
    const key = `\u0000FN-L${linkId++}\u0000`;
    links[key] = `<a href="${url.trim()}">${label.trim()}</a>`;
    return key;
  });
  s = s.replace(/(?<!["'>])(https?:\/\/[^\s<>"')]+)/g, (url: string) => {
    const key = `\u0000FN-L${linkId++}\u0000`;
    links[key] = `<a href="${url}">${url}</a>`;
    return key;
  });

  for (const [re, repl] of simpleInlineTags) {
    s = s.replace(re, repl);
  }
  s = s.replace(/~~(.+?)~~/g, "<del>$1</del>");
  s = s.replace(/\$s(.+?)s\$/gs, (_: string, inner: string) => {
    inner = inner.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
    return `<span class="smoke-text">${inner}</span>`;
  });
  s = s.replace(/\$a(.+?)a\$/gs, (_: string, inner: string) => {
    inner = inner.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
    return `<span class="aurora-text">${inner}</span>`;
  });
  s = s.replace(/\$g(.+?)g\$/gs, (_: string, inner: string) => {
    inner = inner.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
    return `<span class="gold-text">${inner}</span>`;
  });
  s = s.replace(/\$\*(.+?)\*\$/gs, (_: string, inner: string) => {
    inner = inner.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
    return `<span class="sparkle-text">${inner}</span>`;
  });
  s = s.replace(/\$\((.+?)\)\$/gs, (_: string, inner: string) => {
    inner = inner.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
    return `<span class="moon-wrap"><span class="moon-text">${inner}</span></span>`;
  });
  s = s.replace(/\$ag(.+?)ag\$/gs, (_: string, inner: string) => {
    inner = inner.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
    return `<span class="silver-text">${inner}</span>`;
  });
  s = s.replace(/#hx\(([^)]+)\)(.*?)hx#/gs, (_: string, color: string, content: string) => {
    return `<span style="color:${color}">${content}</span>`;
  });
  s = s.replace(/\$hxo\(([^)]+)\)(.*?)hxo#/gs, (_: string, color: string, content: string) => {
    return `<span class="hex-outline" style="--hxo-color:${color}">${content}</span>`;
  });
  s = s.replace(/\$hxa\(([^)]+)\)\(([^)]+)\)\(([^)]+)\)(.*?)hxa\$/gs, (_: string, c1: string, c2: string, c3: string, content: string) => {
    return `<span class="hex-aurora" style="--ha-c1:${c1};--ha-c2:${c2};--ha-c3:${c3}">${content}</span>`;
  });
  s = s.replace(/\$hxas\(([^)]+)\)\(([^)]+)\)\(([^)]+)\)(.*?)hxas\$/gs, (_: string, c1: string, c2: string, c3: string, content: string) => {
    return `<span class="hex-aurora-static" style="--ha-c1:${c1};--ha-c2:${c2};--ha-c3:${c3}">${content}</span>`;
  });
  s = s.replace(/\$hxau\(([^)]+)\)\(([^)]+)\)\(([^)]+)\)(.*?)hxau\$/gs, (_: string, c1: string, c2: string, c3: string, content: string) => {
    return `<span class="hex-aurora-up" style="--ha-c1:${c1};--ha-c2:${c2};--ha-c3:${c3}">${content}</span>`;
  });
  s = s.replace(/\$hxaus\(([^)]+)\)\(([^)]+)\)\(([^)]+)\)(.*?)hxaus\$/gs, (_: string, c1: string, c2: string, c3: string, content: string) => {
    return `<span class="hex-aurora-up-static" style="--ha-c1:${c1};--ha-c2:${c2};--ha-c3:${c3}">${content}</span>`;
  });
  s = s.replace(/\|<(.+?)<\|/gs, (_: string, text: string) => {
    const inner = text.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
    return `<span class="scroll-wrap scroll-left"><span class="scroll-sizer"><span class="scroll-text">${inner}</span></span><span class="scroll-track"><span class="scroll-text">${inner}</span><span class="scroll-text">${inner}</span></span></span>`;
  });
  s = s.replace(/\|>(.+?)>\|/gs, (_: string, text: string) => {
    const inner = text.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
    return `<span class="scroll-wrap scroll-right"><span class="scroll-sizer"><span class="scroll-text">${inner}</span></span><span class="scroll-track"><span class="scroll-text">${inner}</span><span class="scroll-text">${inner}</span></span></span>`;
  });
  for (const [key, val] of Object.entries(links)) {
    s = s.replace(key, val);
  }
  return s.replace(/\n\n/g, "<br><br>").replace(/\n/g, "<br>");
}

export function preprocessMarkdown(text: string, book: string = "gsgw"): string {
  let s = text.replace(/\r\n/g, "\n");

  // transition text — must run first so it splits on ">" before formatting
  // tags convert to HTML (which also contains ">")
  s = s.replace(/\|t\s*(?:\(([^)]*)\))?\s*(.*?)\s*t\|/gs, (_: string, dur: string, text: string) => {
    const parts = text.split(">").map(p => p.trim()).filter(Boolean);
    if (parts.length > 6) {
      return parts[0].replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
    }
    const validDur = dur !== undefined && dur !== null && /^\d+(\.\d+)?(ms|s)$/.test(dur);
    const durStyle = validDur ? `--tt-slot:${dur};` : "";
    const items = parts
      .map((p, i) => `<span class="transition-item" style="--tt-i:${i}">${p.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")}</span>`)
      .join("");
    return `<span class="transition-text" data-count="${parts.length}" style="${durStyle}--tt-count:${parts.length}">${items}</span>`;
  });

  // illustration tags are handled by the template, not here

  s = s.replace(/%%(.*?)%%/gs, '<span class="shake">$1</span>');

  s = s.replace(/%~(.*?)~%/gs, (_: string, inner: string) => {
    return [...inner].map((c: string, i: number) =>
      c === " " ? " " : `<span class="shake" style="animation-delay:-${(i * 0.05) % 0.5}s">${c}</span>`
    ).join("");
  });

  s = s.replace(/%\^(.*?)\^%/gs, (_: string, inner: string) => {
    const len = inner.length;
    return [...inner].map((c: string, i: number) => {
      if (c === " ") return " ";
      const delay = ((len - 1 - i) * 0.05) % 0.5;
      return `<span class="wave-up" style="animation-delay:-${delay}s">${c}</span>`;
    }).join("");
  });

  s = s.replace(/^~~~(?=\s*$)/gm, '<hr class="visible-hr">');
  s = s.replace(/^~\^~(?=\s*$)/gm, '<hr class="invisible-hr">');

  s = s.replace(/@_@(.+?)@_@/gs, (_: string, inner: string) => {
    inner = inner.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
    inner = inner.replace(/\$\$(.+?)\$\$/gs, '<span class="handwritten">$1</span>');
    inner = inner.replace(/\$lat(.+?)lat\$/gs, '<span class="lato">$1</span>');
    inner = inner.replace(/\$fox(.+?)fox\$/gs, '<span class="fox">$1</span>');
    inner = inner.replace(/\$Eb(.+?)Eb\$/gs, '<span class="eb-garamond">$1</span>');
    inner = inner.replace(/\$h(?!x)(.+?)h\$/gs, '<span class="paulo-bittencourt">$1</span>');
    inner = inner.replace(/\$nbg(.+?)nbg\$/gs, '<span class="nanum-barun-gothic">$1</span>');
    inner = inner.replace(/\$tf(.+?)tf\$/gs, '<span class="chungju-kimsaeng">$1</span>');
    inner = inner.replace(/\$vcr(.+?)vcr\$/gs, '<span class="vcr-osd-mono">$1</span>');
    inner = inner.replace(/\$Bh(.+?)Bh\$/gs, '<span class="braun-handwriting">$1</span>');
    inner = inner.replace(/\$c(.+?)c\$/gs, '<span class="contaminated">$1</span>');
    inner = inner.replace(/\$wo(.+?)wo\$/gs, '<span class="outline-white">$1</span>');
    inner = inner.replace(/\$bo(.+?)bo\$/gs, '<span class="outline-black">$1</span>');
    const chars = inner.split(/(<[^>]+>)/).flatMap((part: string) => {
      if (part.startsWith("<") && part.endsWith(">")) return [part];
      return [...part].map(c => c === " " ? " " : `<span class="char">${c}</span>`);
    });
    return `<span class="glitch-subtle">${chars.join("")}</span>`;
  });

  s = s.replace(/#\^#(.+?)#\^#/gs, (_: string, inner: string) => {
    const len = inner.length;
    const chars = [...inner].map((c: string, i: number) => {
      if (c === " ") return " ";
      const scale = 1 + (i / Math.max(len - 1, 1)) * 0.6;
      return `<span class="grow-char" style="font-size:${scale.toFixed(2)}em">${c}</span>`;
    });
    return `<span class="text-grow">${chars.join("")}</span>`;
  });

  s = s.replace(/#v#(.+?)#v#/gs, (_: string, inner: string) => {
    const len = inner.length;
    const chars = [...inner].map((c: string, i: number) => {
      if (c === " ") return " ";
      const scale = 1.4 - (i / Math.max(len - 1, 1)) * 0.4;
      return `<span class="grow-char" style="font-size:${scale.toFixed(2)}em">${c}</span>`;
    });
    return `<span class="text-grow">${chars.join("")}</span>`;
  });

  // Footnotes — superscript reference with tooltip
  s = s.replace(/\[(\d+)\]\{([^}]+)\}/gs, (_: string, num: string, text: string) => {
    const tipHtml = renderFootnoteText(text);
    return `<span class="fn-ref" id="fn-ref-${num}" tabindex="0" role="button">[${num}]<span class="fn-tip"><strong>${num}.</strong> ${tipHtml}</span></span>`;
  });

  const placeholders = new Map<string, string>();
  let pid = 0;
  s = s.replace(/!\[.*?\]\(.*?\)/g, (m: string) => { const k = `\x00IMG${pid++}\x00`; placeholders.set(k, m); return k; });

  for (const [re, repl] of simpleInlineTags) {
    s = s.replace(re, repl);
  }

  // Strikethrough — after inline tags so color/format markers inside are already wrapped
  s = s.replace(/~~(.+?)~~/g, "<del>$1</del>");

  // Triple strikethrough — after inline tags so inner formatting is already wrapped
  s = s.replace(/<ts>([\s\S]*?)<\/ts>/g, "<span class=\"triple-strike\">$1</span>");

  // Scroll text — duplicate content for seamless marquee loop
  s = s.replace(/\|<(.+?)<\|/gs, (_: string, text: string) => {
    const inner = text.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
    return `<span class="scroll-wrap scroll-left"><span class="scroll-sizer"><span class="scroll-text">${inner}</span></span><span class="scroll-track"><span class="scroll-text">${inner}</span><span class="scroll-text">${inner}</span></span></span>`;
  });
  s = s.replace(/\|>(.+?)>\|/gs, (_: string, text: string) => {
    const inner = text.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
    return `<span class="scroll-wrap scroll-right"><span class="scroll-sizer"><span class="scroll-text">${inner}</span></span><span class="scroll-track"><span class="scroll-text">${inner}</span><span class="scroll-text">${inner}</span></span></span>`;
  });

  for (const [key, val] of placeholders) {
    s = s.replace(key, val);
  }

  s = s.replace(/#hx\(([^)]+)\)(.*?)hx#/gs, (_: string, color: string, content: string) => {
    return `<span style="color:${color}">${content}</span>`;
  });

  s = s.replace(/\$hxo\(([^)]+)\)(.*?)hxo#/gs, (_: string, color: string, content: string) => {
    return `<span class="hex-outline" style="--hxo-color:${color}">${content}</span>`;
  });

  s = s.replace(/\$hxa\(([^)]+)\)\(([^)]+)\)\(([^)]+)\)(.*?)hxa\$/gs, (_: string, c1: string, c2: string, c3: string, content: string) => {
    return `<span class="hex-aurora" style="--ha-c1:${c1};--ha-c2:${c2};--ha-c3:${c3}">${content}</span>`;
  });

  s = s.replace(/\$hxas\(([^)]+)\)\(([^)]+)\)\(([^)]+)\)(.*?)hxas\$/gs, (_: string, c1: string, c2: string, c3: string, content: string) => {
    return `<span class="hex-aurora-static" style="--ha-c1:${c1};--ha-c2:${c2};--ha-c3:${c3}">${content}</span>`;
  });

  s = s.replace(/\$hxau\(([^)]+)\)\(([^)]+)\)\(([^)]+)\)(.*?)hxau\$/gs, (_: string, c1: string, c2: string, c3: string, content: string) => {
    return `<span class="hex-aurora-up" style="--ha-c1:${c1};--ha-c2:${c2};--ha-c3:${c3}">${content}</span>`;
  });

  s = s.replace(/\$hxaus\(([^)]+)\)\(([^)]+)\)\(([^)]+)\)(.*?)hxaus\$/gs, (_: string, c1: string, c2: string, c3: string, content: string) => {
    return `<span class="hex-aurora-up-static" style="--ha-c1:${c1};--ha-c2:${c2};--ha-c3:${c3}">${content}</span>`;
  });

  s = s.replace(/@@([^@]+)@@/gs, (_: string, inner: string) => {
    inner = inner.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
    const chars = inner.split(/(<[^>]+>)/).flatMap((part: string) => {
      if (part.startsWith("<") && part.endsWith(">")) return [part];
      return [...part].map(c => c === " " ? " " : `<span class="char">${c}</span>`);
    });
    return `<span class="glitch-text">${chars.join("")}</span>`;
  });

  s = s.replace(/\$s(.+?)s\$/gs, (_: string, inner: string) => {
    inner = inner.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
    return `<span class="smoke-text">${inner}</span>`;
  });

  s = s.replace(/\$a(.+?)a\$/gs, (_: string, inner: string) => {
    inner = inner.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
    return `<span class="aurora-text">${inner}</span>`;
  });

  s = s.replace(/\$g(.+?)g\$/gs, (_: string, inner: string) => {
    inner = inner.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
    return `<span class="gold-text">${inner}</span>`;
  });

  s = s.replace(/\$\*(.+?)\*\$/gs, (_: string, inner: string) => {
    inner = inner.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
    return `<span class="sparkle-text">${inner}</span>`;
  });

  s = s.replace(/\$\((.+?)\)\$/gs, (_: string, inner: string) => {
    inner = inner.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
    return `<span class="moon-wrap"><span class="moon-text">${inner}</span></span>`;
  });

  s = s.replace(/\$ag(.+?)ag\$/gs, (_: string, inner: string) => {
    inner = inner.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
    return `<span class="silver-text">${inner}</span>`;
  });

  s = s.replace(/\}([^}]+)\}/g, (_: string, content: string) => {
    const text = content.trim();
    if (text.startsWith("[!]")) return `<span class="alert-sub alert-sub-left">${text.slice(3).trim()}</span>`;
    return `<span class="debut-achievement-sub debut-achievement-sub-left">${text}</span>`;
  });
  s = s.replace(/\{([^{]+)\{/g, (_: string, content: string) => {
    const text = content.trim();
    if (text.startsWith("[!]")) return `<span class="alert-sub alert-sub-right">${text.slice(3).trim()}</span>`;
    return `<span class="debut-achievement-sub debut-achievement-sub-right">${text}</span>`;
  });

  s = s.replace(/\+[-+]+\n(.*?)\n[-+]+\+/gs, (_: string, inner: string) => {
    const noMeta = inner.trimStart().startsWith("\\");
    if (noMeta) inner = inner.replace("\\", "");
    return makeWindow("wiki-window", inner, noMeta ? "no-meta" : undefined);
  });

  s = s.replace(/\+[=]+\n(.*?)\n[=]+\+/gs, (_: string, inner: string) => makeWindow("black-window", inner));

  s = s.replace(/\+[~]+\n(.*?)\n[~]+\+/gs, (_: string, inner: string) => {
    const noFl = inner.trimStart().startsWith("\\");
    if (noFl) inner = inner.replace("\\", "");
    return makeWindow("system-window", inner, noFl ? "no-fl-dividers" : undefined);
  });

  s = s.replace(/\+\$\n(.*?)\n\$\+/gs, (_: string, inner: string) => makeWindow("plain-window", inner));

  s = s.replace(/\+\.\n(.*?)\n\.\+/gs, (_: string, inner: string) => makeWindow("bare-window", inner));

  s = s.replace(/&[-]+\n(.*?)\n[-]+&/gs, (_: string, inner: string) => {
    const noMeta = inner.trimStart().startsWith("\\");
    if (noMeta) inner = inner.replace("\\", "");
    return makeWindow("record-window", inner, noMeta ? "no-meta" : undefined);
  });

  s = s.replace(/&\$\n(.*?)\n\$&/gs, (_: string, inner: string) => makeWindow("followup-window", inner));

  s = s.replace(/![-]+\n(.*?)\n[-]+!/gs, (_: string, inner: string) => {
    const noMeta = inner.trimStart().startsWith("\\");
    if (noMeta) inner = inner.replace("\\", "");
    return makeWindow("note-window", inner, noMeta ? "no-meta" : undefined);
  });

  s = s.replace(/!\$\n(.*?)\n\$!/gs, (_: string, inner: string) => makeWindow("sticky-window", inner));

  s = s.replace(/!pb\n(.*?)\npb!/gs, (_: string, inner: string) => makeWindow("paper-boat", inner));

  s = s.replace(/!\[\n(.*?)\n\]!/gs, (_: string, inner: string) => makeWindow("braun-screen", inner));

  s = s.replace(/\$Brt\n(.*?)\nBrt\$/gis, (_: string, inner: string) => "\n" + makeWindow("braun-tv-text", toParagraphs(fmtInline(inner))) + "\n");
  s = s.replace(/\$Brd\n(.*?)\nBrd\$/gis, (_: string, inner: string) => "\n" + makeWindow("braun-doll-text", toParagraphs(fmtInline(inner))) + "\n");
  s = s.replace(/\$p\n(.*?)\np\$/gs, (_: string, inner: string) => "\n" + makeWindow("padding-window", toParagraphs(fmtInline(inner))) + "\n");

  s = s.replace(/★!\n(.*?)\n!★/gs, (_: string, inner: string) => makeWindow("debut-alert", inner));

  s = s.replace(/★:\n([\s\S]*?)\n:★/gs, (_: string, inner: string) => {
    const SPEAKER_COLORS: Record<string, string> = {
      PMD: "#FFF8D9", SAH: "#FFF0E1", BSJ: "#EDF5FF",
      LSJ: "#F2ECFF", KRB: "#FDE8F1", CE: "#FFE5E5",
      RCW: "#EAF8F2"
    };
    const SPEAKERS = Object.keys(SPEAKER_COLORS);
    const DASH = "[-–—]";

    function parseLine(raw: string): string {
      const trimmed = raw.trim();
      if (!trimmed) return "";

      const dashPrefixRe = new RegExp(`^${DASH}\\s*(.+)`);
      const dashSuffixRe = new RegExp(`(.+)\\s*${DASH}$`);

      const isLeft = dashPrefixRe.test(trimmed);
      const isRight = !isLeft && dashSuffixRe.test(trimmed);

      let content = trimmed;
      if (isLeft) content = trimmed.replace(dashPrefixRe, "$1");
      else if (isRight) content = trimmed.replace(dashSuffixRe, "$1");

      const speakerRe = new RegExp(`^(${SPEAKERS.join("|")}):\\s*(.*)`);
      const sp = content.match(speakerRe);
      const speaker = sp?.[1] ?? null;
      const message = sp ? sp[2] : content;

      const color = speaker ? SPEAKER_COLORS[speaker] : null;
      const style = color ? ` style="background:${color};color:#222"` : "";
      const align = isLeft ? "sms-left" : isRight ? "sms-right" : "sms-center";

      return `<div class="sms-bubble ${align}"${style}>${escapeHtml(imgInline(fmtInline(message), book))}</div>`;
    }

    const bubbles = inner.split("\n").map(parseLine).filter(Boolean).join("\n");
    return makeWindow("sms-window", bubbles);
  });

  s = s.replace(/★\$\n([\s\S]*?)\n\$★/gs, (_: string, inner: string) => {
    const lines = inner.split("\n");
    let title = "";
    let desc = "";
    const items: { text: string; depth: number }[] = [];
    let inComments = false;

    for (const raw of lines) {
      const line = raw.trim();
      if (line.startsWith("[")) {
        title = escapeHtml(imgInline(fmtInline(line.trim()), book));
      } else if (line.startsWith(":")) {
        desc = escapeHtml(imgInline(fmtInline(line.replace(/^:/, "").trim()), book));
      } else if (line.startsWith("-") || line.startsWith("\u2013") || line.startsWith("\u2014")) {
        inComments = true;
        const content = line.replace(/^[\u2014\u2013-]/, "").trim();
        items.push({ text: escapeHtml(imgInline(fmtInline(content), book)), depth: 0 });
      } else if (line.startsWith("\u2937") || line.startsWith("\u2514") || line.startsWith("\u221F")) {
        inComments = true;
        let depth = 0;
        let content = line;
        while (content.startsWith("\u2937") || content.startsWith("\u2514") || content.startsWith("\u221F")) {
          depth++;
          content = content.replace(/^[⤷└∟]/, "").trimStart();
        }
        if (depth > 3) depth = 3;
        items.push({ text: escapeHtml(imgInline(fmtInline(content.trim()), book)), depth });
      } else if (line && !inComments) {
        desc += (desc ? "</p>\n<p>" : "<p>") + escapeHtml(imgInline(fmtInline(line), book));
      }
    }

    let html = "";
    if (title || desc) {
      html += '<div class="comment-post-header">\n';
      if (title) html += `<div class="comment-post-title">${title}</div>\n`;
      if (desc) html += `<div class="comment-post-desc">${desc}</p></div>\n`;
      html += "</div>\n";
    }
    if (items.length) {
      html += '<div class="comment-section">\n';
      for (const item of items) {
        if (item.depth === 0) {
          html += `<div class="comment">${item.text}</div>\n`;
        } else {
          html += `<div class="comment-reply depth-${item.depth}"><span class="reply-icon">⤷</span><span class="reply-body">${item.text}</span></div>\n`;
        }
      }
      html += "</div>\n";
    }
    return makeWindow("alert-window", html);
  });

  s = s.replace(/★=\n(.*?)\n=★/gs, (_: string, inner: string) => {
    const lines = inner.split("\n");
    let title = lines[0].trim();
    if (title.startsWith("\\")) {
      title = "";
      lines[0] = lines[0].replace("\\", "").trim();
    }
    const bodyRaw = (title ? lines.slice(1) : lines).join("\n").trim();
    const body = bodyRaw
      .replace(/\[\s*\n([\s\S]*?)\n\s*\]/g, (_m: string, inner: string) => {
        const items = inner.split("\n").map((l: string) => l.trim()).filter((l: string) => l);
        const itemHtml = items.map((item: string) =>
          `<div class="debut-achievement-list-item">${item}</div>`
        ).join("\n<div class=\"debut-achievement-list-divider\"></div>\n");
        return `<div class="debut-achievement-list">\n${itemHtml}\n</div>`;
      })
      .replace(/^\s*\[(.+?)\]\s*$/gm, (_m: string, content: string) => {
        return `<div class="debut-achievement-list">\n<div class="debut-achievement-list-item">${content}</div>\n</div>`;
      });
    const titleHtml = title ? `<div class="debut-window-title">${title}</div>\n\n` : "";
    return makeWindow("debut-achievement", titleHtml + body);
  });

  s = s.replace(/★-\n(.*?)\n-★/gs, (_: string, inner: string) => {
    const lines = inner.split("\n");
    let title = lines[0].trim();
    if (title.startsWith("\\")) {
      title = "";
      lines[0] = lines[0].replace("\\", "").trim();
    }
    const bodyLines = (title ? lines.slice(1) : lines).map((l: string) => {
      const m = l.match(/^\s*\[(.+?)\]\s*$/);
      if (m) return `<div class="debut-window-label">${m[1]}</div>`;
      return l;
    });
    const body = bodyLines.join("\n").trim();
    const titleHtml = title ? `<div class="debut-window-title">${title}</div>\n\n` : "";
    return makeWindow("debut-window", titleHtml + body);
  });

  s = replaceTwitterUrls(s);
  return s;
}
