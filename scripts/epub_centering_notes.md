# EPUB reader compatibility

## One build per book part

The download/release workflow builds a single EPUB edition for each book part:

```sh
python3 scripts/build_new_epub.py --book gsgw --part part1 --no-fetch-twitter
```

Output: `scripts/epub/Got.Dropped.into.a.Ghost.Story.Still.Gotta.Work.-.Part.1.PlainText.epub`.
There are no reader profiles, reader-specific output names, or alternate effect
modes. GSGW and Debut use the same pipeline. The release workflow installs
`fonttools` and `brotli` alongside the existing dependencies.

## Gradual sizing and pagination

Long growing/shrinking letter effects using per-letter `em` sizes caused enormous
page-count increases around chapters 80–81 in Moon+ Reader. The user confirmed
that explicit `rem` values preserve the gradual effect without that problem.
Enclosing inline scales are included in each value: 1.5 × 1.6em becomes 2.4rem.
All chapter text and nested emphasis are preserved. This applies to EPUB output;
website rendering is separate.

## Scare pages and chapter labels

Scares and story continuations remain separate XHTML spine files. Only chapter
starts appear in the TOC. Hidden chapter headings label the other files correctly
in Episteme, which otherwise invents a title from the spine position.

The existing scare-page viewport sizing and table-cell centering are retained.
Mandatory scroll snapping was removed after publisher preview became trapped on
scare pages. Every story/scare section ends with a paragraph-based forced page
break. Paged mode isolates the scares; continuous-scroll behavior varies by reader.
The earlier content-sized/top-aligned layout was an interim compatibility change,
not the final single-edition design.

## Fonts and encoding

CSS-referenced fonts are embedded as static TrueType/OpenType files, converted
with `fonttools` and `brotli`. Separate supplied bold/italic faces are preserved.
Variable fonts use their default axes, with weight clamped to the CSS face's
range. Fonts are subset to the book's characters, common punctuation, and
CSS-generated content, retaining OpenType features, hinting, and font names.
Fonts marked as prohibiting subsetting are kept whole. The cache is
`scripts/epub/converted_fonts/`, keyed by the character set. Font URLs and OPF
entries are generated from the same assets rather than duplicate lists.

Generated XHTML includes both the XML UTF-8 declaration and HTML `meta charset`.
The HTML declaration hardens preview paths that showed garbled punctuation; it
is not a confirmed font-loading fix.

## Known publisher-preview limitation

The user's Moon+ Reader Pro 10.1 with Google Android System WebView
156.0.8078.47 substitutes special fonts in publisher preview. The same embedded
fonts work in Chrome on the same phone. Stronger CSS priority, inline font
selection, and inline font data did not fix preview. No EPUB-side workaround has
been confirmed. The one-off diagnostic generator has been removed; existing test
artifacts and Drive uploads are retained.

The official Pro Play listing advertised v10.8 with embedded-font CSS rendering
improvements during investigation, but no preview fix was verified:
https://play.google.com/store/apps/details?id=com.flyersoft.moonreaderp
