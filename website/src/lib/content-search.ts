export interface Chapter {
  title: string;
  slug: string | number;
  category?: string;
  index?: number;
  thumb?: string | null;
}

export interface ContentMatch {
  chapter: Chapter;
  snippet: string;
  line: number;
}

const REPO = "EnderOksam/GSGW-Reader";
const BRANCH = "main";

function tlDir(book: string, tl: string): string {
  if (book === "debut" && tl === "debutplaintxt") return "DebutPlainTxt";
  if (book === "debut" && tl === "debutformatted") return "DebutFormatted";
  return tl;
}

async function fetchChapterContent(book: string, tl: string, index: number, signal?: AbortSignal): Promise<string> {
  const dir = tlDir(book, tl);
  const filename = String(index + 1).padStart(4, "0") + ".md";
  const url = `https://raw.githubusercontent.com/${REPO}/${BRANCH}/chapters/${book}/${dir}/${filename}`;
  const res = await fetch(url, { signal });
  if (!res.ok) return "";
  return res.text();
}

function cleanContentForSearch(text: string): string {
  let t = text.replace(/^---[\s\S]*?---\n?/, "");
  // Strip block delimiters but keep inner content
  t = t
    .replace(/★[\-=!:$]\n?([\s\S]*?)\n?[\-=!:$]★/g, "$1")
    .replace(/\$★\n?([\s\S]*?)\n?★\$/g, "$1")
    .replace(/\+[-=~\$]+\n?([\s\S]*?)\n?[-=~\$]+\+/g, "$1")
    .replace(/[&][-\$]+\n?([\s\S]*?)\n?[-\$]+[&]/g, "$1")
    .replace(/[!][-\$[\]]+\n?([\s\S]*?)\n?[\-\$[\]]+!/g, "$1")
    .replace(/\$Brt\n?([\s\S]*?)\n?Brt\$/gi, "$1")
    .replace(/\$Brd\n?([\s\S]*?)\n?Brd\$/gi, "$1")
    .replace(/!pb\n?([\s\S]*?)\n?pb!/g, "$1")
    .replace(/\$p\n?([\s\S]*?)\n?p\$/g, "$1");
  // Strip standalone delimiter lines (scene breaks)
  t = t
    .replace(/^[\-\u2013\u2014~=]{3,}$/gm, "")
    .replace(/^\*\s\*\s\*$/gm, "")
    .replace(/^\*{3,}$/gm, "")
    .replace(/^[\+\=&!~#\^v]+$/gm, "")
    .replace(/^\[.*?\]$/gm, "")
    .replace(/^@[\w.]+$/gm, "")
    .replace(/^- (?:BSJ|LSJ|PMD|SAH|KRB|CE|RCW):.*/gim, "")
    .replace(/^(?:BSJ|LSJ|PMD|SAH|KRB|CE|RCW):.*/gim, "");
  // Strip inline delimiter markers but keep inner text
  t = t
    .replace(/#\^[>f<]?\^#([\s\S]*?)#\^[>f<]?\^#/g, "$1")
    .replace(/#v[>f<]?v#([\s\S]*?)#v[>f<]?v#/g, "$1")
    .replace(/#f[><]?#(.*?)#f[><]?#/g, "$1")
    .replace(/#\*(.*?)\*#/g, "$1")
    .replace(/#><(.*?)><#/g, "$1")
    .replace(/#r(.*?)r#/g, "$1")
    .replace(/#o(.*?)o#/g, "$1")
    .replace(/#y(.*?)y#/g, "$1")
    .replace(/#g(.*?)g#/g, "$1")
    .replace(/#cy(.*?)cy#/g, "$1")
    .replace(/#b(.*?)b#/g, "$1")
    .replace(/#lp(.*?)lp#/g, "$1")
    .replace(/#p(.*?)p#/g, "$1")
    .replace(/;r(.*?)r;/g, "$1")
    .replace(/;o(.*?)o;/g, "$1")
    .replace(/;y(.*?)y;/g, "$1")
    .replace(/;g(.*?)g;/g, "$1")
    .replace(/;b(.*?)b;/g, "$1")
    .replace(/;p(.*?)p;/g, "$1")
    .replace(/\$c(.*?)c\$/g, "$1")
    .replace(/\$\$(.*?)\$\$/g, "$1")
    .replace(/~~(.*?)~~/g, "$1")
    .replace(/%%(.*?)%%/g, "$1")
    .replace(/%~(.*?)~%/g, "$1")
    .replace(/%\^(.*?)\^%/g, "$1")
    .replace(/@@(.*?)@@/g, "$1")
    .replace(/@_@(.*?)@_@/g, "$1")
    .replace(/\$\*(.*?)\*\$/g, "$1")
    .replace(/\$\((.*?)\)\$/g, "$1")
    .replace(/\$s(.*?)s\$/g, "$1")
    .replace(/\$a(.*?)a\$/g, "$1")
    .replace(/\$g(.*?)g\$/g, "$1")
    .replace(/\$ag(.*?)ag\$/g, "$1")
    .replace(/\$\[★\](.*?)\[★\]\$/g, "$1")
    .replace(/\}[!]?([^\n}]+)\}/g, "$1")
    .replace(/\{[!]?([^\n{]+)\{/g, "$1")
    .replace(/@ll@|@rr@|@cc@|@l@|@r@|@c@/g, "")
    .replace(/^\\(.*)$/gm, "$1")
    .replace(/\{style="[^"]*"\}/g, "");
  // Collapse whitespace
  t = t
    .replace(/\n{3,}/g, "\n\n")
    .replace(/[ \t]+/g, " ")
    .trim();
  return t;
}

function cleanSnippet(raw: string): string {
  let t = raw
    .replace(/★[\-=!:$][\s\S]*?[\-=!:$]★/g, "")
    .replace(/\$[★][\s\S]*?[★]\$/g, "")
    .replace(/\+[-=~\$]+[\s\S]*?[-=~\$]+\+/g, "")
    .replace(/[&][-\$]+[\s\S]*?[-\$]+[&]/g, "")
    .replace(/[!][-\$[\]]+[\s\S]*?[-\$[\]]+!/g, "")
    .replace(/\$Brt[\s\S]*?Brt\$/gi, "")
    .replace(/\$Brd[\s\S]*?Brd\$/gi, "")
    .replace(/!pb[\s\S]*?pb!/g, "")
    .replace(/\$p[\s\S]*?p\$/g, "")
    .replace(/^[\+][-=~\$*><]+[\+]*$/gm, "")
    .replace(/^[\&][-\$]+[\-&\$]*$/gm, "")
    .replace(/^![\-\$\[\]!]+$/gm, "")
    .replace(/^[\-\u2013\u2014~]{3,}$/gm, "")
    .replace(/^\*{3,}$/gm, "")
    .replace(/^[\+\=&!~#\^v]+$/gm, "")
    .replace(/\$\$[\s\S]*?\$\$/g, "")
    .replace(/~~[\s\S]*?~~/g, "")
    .replace(/%%[\s\S]*?%%/g, "")
    .replace(/%~[\s\S]*?~%/g, "")
    .replace(/%\^[\s\S]*?\^%/g, "")
    .replace(/@@[\s\S]*?@@/g, "")
    .replace(/@_@[\s\S]*?@_@/g, "")
    .replace(/\$\*[\s\S]*?\*\$/g, "")
    .replace(/\$\([\s\S]*?\)\$/g, "")
    .replace(/\$s[\s\S]*?s\$/g, "")
    .replace(/\$a[\s\S]*?a\$/g, "")
    .replace(/\$g[\s\S]*?g\$/g, "")
    .replace(/\$ag[\s\S]*?ag\$/g, "")
    .replace(/\$c[\s\S]*?c\$/g, "")
    .replace(/#\^[>f<]?\^#[\s\S]*?#\^[>f<]?\^#/g, "")
    .replace(/#v[>f<]?v#[\s\S]*?#v[>f<]?v#/g, "")
    .replace(/#f[><]?#(.*?)#f[><]?#/g, "$1")
    .replace(/#\*(.*?)\*#/g, "$1")
    .replace(/#><(.*?)><#/g, "$1")
    .replace(/#r(.*?)r#/g, "$1")
    .replace(/#o(.*?)o#/g, "$1")
    .replace(/#y(.*?)y#/g, "$1")
    .replace(/#g(.*?)g#/g, "$1")
    .replace(/#cy(.*?)cy#/g, "$1")
    .replace(/#b(.*?)b#/g, "$1")
    .replace(/#lp(.*?)lp#/g, "$1")
    .replace(/#p(.*?)p#/g, "$1")
    .replace(/;r(.*?)r;/g, "$1")
    .replace(/;o(.*?)o;/g, "$1")
    .replace(/;y(.*?)y;/g, "$1")
    .replace(/;g(.*?)g;/g, "$1")
    .replace(/;b(.*?)b;/g, "$1")
    .replace(/;p(.*?)p;/g, "$1")
    .replace(/@l@|@r@|@c@|@ll@|@rr@/g, "")
    .replace(/\}[\!]?([^\n}]+)\}/g, "")
    .replace(/\{[\!]?([^\n{]+)\{/g, "")
    .replace(/^\[.*?\]$/gm, "")
    .replace(/^- (?:BSJ|LSJ|PMD|SAH|KRB|CE|RCW):.*/gim, "")
    .replace(/^(?:BSJ|LSJ|PMD|SAH|KRB|CE|RCW):.*/gim, "")
    .replace(/^@[\w.]+$/gm, "")
    .replace(/^\\(.*)$/gm, "$1")
    .replace(/\{style="[^"]*"\}/g, "")
    .replace(/\n{3,}/g, "\n\n")
    .replace(/[ \t]+/g, " ")
    .trim();
  return t;
}

function highlightMatch(text: string, query: string): string {
  if (!query) return text;
  const escaped = query.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  return text.replace(new RegExp(`(${escaped})`, "gi"), '<mark style="background: rgba(168,85,247,0.2); color: #c084fc; border-radius: 4px; padding: 0 4px;">$1</mark>');
}

export function renderSnippet(raw: string, query: string): string {
  let text = cleanSnippet(raw);
  text = text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
  text = text
    .replace(/\\([<>])/g, "$1")
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.+?)\*/g, "<em>$1</em>")
    .replace(/_(.+?)_/g, "<u>$1</u>")
    .replace(/~~(.+?)~~/g, "<s>$1</s>")
    .replace(/\$\$(.+?)\$\$/g, "$1");
  const lines = text.split("\n");
  const rendered = lines.map((l) => l.trim()).join("<br>");
  return highlightMatch(rendered, query);
}

const SNIPPET_KEY = "searchSnippetTarget";

export function storeSnippetTarget(snippet: string, query: string): void {
  sessionStorage.setItem(SNIPPET_KEY, JSON.stringify({ snippet, query }));
}

export function consumeSnippetTarget(): { snippet: string; query: string } | null {
  const raw = sessionStorage.getItem(SNIPPET_KEY);
  if (!raw) return null;
  sessionStorage.removeItem(SNIPPET_KEY);
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export function searchChapterContent(
  query: string,
  chapters: Chapter[],
  titleSlugMatches: Chapter[],
  bookSlug: string,
  selectedTL: string,
  onResult: (matches: Map<string, ContentMatch>) => void,
  onStart: () => void,
  onEnd: () => void,
  signal?: AbortSignal,
): void {
  if (query.length < 3) {
    onEnd();
    return;
  }

  onStart();
  const lowerQuery = query.toLowerCase();
  const titleSlugSlugs = new Set(titleSlugMatches.map((c) => c.slug.toString()));
  const chaptersToSearch = chapters.filter((c) => !titleSlugSlugs.has(c.slug.toString()));

  const CONCURRENCY = 10;

  (async () => {
    const matches = new Map<string, ContentMatch>();
    for (let i = 0; i < chaptersToSearch.length; i += CONCURRENCY) {
      if (signal?.aborted) break;
      const batch = chaptersToSearch.slice(i, i + CONCURRENCY);
      const results = await Promise.allSettled(
        batch.map(async (ch) => {
          const content = await fetchChapterContent(bookSlug, selectedTL, ch.index ?? 0, signal);
          const cleaned = cleanContentForSearch(content);
          const idx = cleaned.toLowerCase().indexOf(lowerQuery);
          if (idx === -1) return null;
          const allLines = cleaned.split("\n");
          let matchLine = 0;
          let pos = 0;
          for (let l = 0; l < allLines.length; l++) {
            if (pos + allLines[l].length >= idx) { matchLine = l; break; }
            pos += allLines[l].length + 1;
          }
          const start = Math.max(0, matchLine - 3);
          const end = Math.min(allLines.length, matchLine + 4);
          const snippet = allLines.slice(start, end).join("\n").trim();
          if (!snippet) return null;
          return { chapter: ch, snippet: snippet.length > 500 ? snippet.slice(0, 500) + "..." : snippet, line: matchLine };
        })
      );
      for (const r of results) {
        if (r.status === "fulfilled" && r.value) {
          matches.set(r.value.chapter.slug.toString(), r.value);
        }
      }
    }
    if (!signal?.aborted) {
      onResult(matches);
      onEnd();
    }
  })();
}
