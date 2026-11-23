# EPUB reader compatibility

## Styled and Legacy variants

The builder offers `--variant styled` and `--variant legacy`. Omitting
`--variant` builds both, as in the original Styled/Legacy release pipeline.
The Styled renderer and `epub.css` retain their original formatting behavior.
Only Legacy runs the transformations in `epub_legacy.py` and
`epub_legacy_fonts.py`; the obsolete `epub-legacy.css` has been removed.
Source conversion retains original images for both editions. Styled embeds those
original assets, including WebP. Legacy's final packaging step converts
illustrations and covers to JPEG, after resizing,
centering and credit composition. Existing compatible JPEGs are reused without
recompression, and content-based cache names prevent collisions between books.
Legacy's tiny Unicode glyph images remain lossless PNGs; vectors stay unchanged.
JPEG conversion and asset rewriting live in `epub_legacy.py`; Styled never calls
them. Debut windows retain the old Legacy plaintext presentation: bold text,
titles and labels at the surrounding size, inline sublabels, inherited alignment,
and no decorative achievement dividers.

## Legacy edition

Legacy uses EPUB 2 formatting calibrated for 600 × 800 readers:

```sh
python3 scripts/build_new_epub.py --book gsgw --part part1 --variant legacy --no-fetch-twitter
python3 scripts/build_new_epub.py --testpage --variant legacy --no-fetch-twitter
```

The full part is saved as
`scripts/epub/Got.Dropped.into.a.Ghost.Story.Still.Gotta.Work.-.Part.1.Legacy.epub`.
The diagnostic is `scripts/epub/Formatting.Test.Page.Legacy.epub`.
It tests fonts, alignment, wiki/record borders, comments, short/long scares, and
a full-page illustration through the same pipeline. `--complete`,
`--limit`, and `--chapter` also work with Legacy. `--variant styled` retains
EPUB 3, original image assets and dimensions, the original fonts and scare-page splitting.

The Legacy profile uses a 540 × 700px usable area: 30px side/top margins, 20px bottom margin,
and an additional allowance for reader chrome. The following are build-time
adaptations, pending testing on the actual device:

- Bitmaps, including covers and cached tweet illustrations, use grayscale PNG
  intermediates, composited onto white and reduced without changing aspect
  ratio or upscaling. Page images are at most 540px wide; all stored bitmaps,
  including inline Unicode glyph images, are at most 600px wide. Both XHTML attributes and inline pixel dimensions record
  the display size. Smaller authored pixel/percentage widths are mapped to the
  screen and baked into the bitmap files as well as the XHTML dimensions.
- The Chapter 1 picture `ch1_1.webp` (also referred to as `0001_1`) uses half
  its normal Legacy size: 270 × 270px rather than 540 × 540px, centered within a 540px-wide bitmap
  column. Every illustration receives horizontal bitmap padding to center it
  within its available column, so placement does not rely on CSS margins. The source artwork
  and standard edition are unchanged.
- Every embedded face is a static TrueType font with real quadratic `glyf`
  outlines, including fonts originally supplied as CFF OpenType. Original
  supplied bold/italic outlines are retained. Each baked face has its own family
  name and is selected directly on the text, including nested emphasis. This
  avoids reliance on the old reader's font-family weight/style matching and
  prevents two books' subsets from sharing a font identity. This is a hardening
  change; device rendering still needs testing. Variable fonts are now
  instantiated at the website's actual weights, including Noto Sans 600 for wiki,
  record, plain, and follow-up window text and 700 for their bold passages.
  Supplied italic faces are used where available. Where the website relies on
  browser-synthesized italics, the legacy build bakes the oblique outlines into
  a separate static face and uses normal CSS font-style to avoid a reader font
  substitution. Descendant rules such as Nanum Barun Gothic strong=400 and Noto
  Sans strong=600 are resolved with CSS specificity rather than flattened.
- Wiki and record windows have literal `===` rules above and below them.
  Padding wrappers (`$p`), windows, Braun text wrappers, and bare windows get
  actual nonbreaking-space/`<br />` paragraphs before and after their contents.
  These do not depend on CSS margins or padding to create the blank line.
  Consecutive and nested wrappers retain their own spacer runs. Blank lines
  are not collapsed. Markdown `***` scene breaks get two extra literal blank
  lines above and below the rule.
  Bold keeps the surrounding font size; only the weight changes.
- Plain text messages follow the website's plaintext window CSS: `- message`
  on the left, `message -` on the right, and `- notice -` in the center. These are
  literal markers, with the reader's native monospace family selected directly.
  Comment threads (`alert-window`) follow the supplied website screenshots:
  literal `-----------` lines surround only the post header; descriptions are
  italic; top-level comments have `- ` markers; nested replies use literal `∟`
  and hanging indents. The Chapter 1 employee-ID header is not bracketed.
- Unicode is no longer replaced with ASCII. When the active font lacks a BMP
  character, the builder chooses an embedded font containing the actual glyph
  and writes its family directly on that run. This covers `∟`, `⤷`, box drawing,
  symbols, and Korean/CJK. Supplementary-plane runs (including mathematical
  styled letters and emoji) are rendered from their real glyph outlines to small
  inline PNGs, with original text retained as `alt`/`title`. This avoids depending
  on old supplementary Unicode support, at the cost of those runs being images
  rather than selectable text. No letter or symbol is approximated by ASCII.
  The build fails with a list of characters if no bundled font covers them.
  Additional open-licensed fallback fonts and their licenses are in
  `legacy_fonts/`. Run `python3 scripts/epub_legacy.py` to regenerate the
  supplemental subsets, or add `--check` to check every release chapter offline
  without creating EPUB archives. Font sources are pinned and cached under
  `scripts/epub/legacy_font_sources/`; commit the resulting font files.
- Only `bare-window`, `braun-screen`, and `black-window` retain box styling.
  Bare/black boxes have one line of internal vertical padding (`1.5em`,
  matching the text line-height). Braun uses 2em text, two internal lines
  (`3em` at that size), natural wrapping/height, and avoids splitting a short
  screen across pages. Braun scare pages skip calculated vertical-centering
  blank lines; normal box padding and the outside blank line remain. All three retain `1em` horizontal padding and one
  literal blank-line paragraph outside each edge. No extra spacer is inserted inside the border. Other
  windows keep their text formatting and independent blank lines without boxes.
- Authored text colors are restored. Opacity is baked into each run's RGB ink
  rather than relying on reader opacity support. Left/right fades become
  character runs with progressively blended colors; supplementary glyph
  bitmaps use the same foreground/background colors. The Legacy maps these to
  gray levels. For e-ink, ink channels are darkened to 65%, with luminance capped
  at 112 on light backgrounds; hues and a useful gray range remain. Directional left/right fades retain their v7 range and white endpoint,
  bypassing this darkening. Black and Braun boxes force pure white text and supplementary glyphs, ignoring authored
  colors, opacity and fading inside those boxes. A nested white bare box resets
  that policy. Original illustration bitmaps remain grayscale.
- Nanum Barun Gothic is raised by 100 at every requested weight, including
  fallback glyphs. Existing 300/400 faces are used when they match. Missing
  500/800 weights are baked as static TrueType outlines using
  [FreeType outline emboldening](https://freetype.org/freetype2/docs/reference/ft2-outline_processing.html#ft_outline_emboldenxy),
  retaining normal face aliases so the Legacy need not synthesize a weight.
- Leading `<br />` runs are anchored with nonbreaking spaces, so old RMSDK
  cannot discard their empty first lines. Numbered lists inside wiki/record/
  plain/follow-up windows become explicit numbered paragraphs; consecutive
  breaks become ordinary blank paragraphs. This fixes the Chapter 21 guide
  without native list indentation or continuation-font behavior. Numbered lists
  have zero extra vertical margins/padding. Their intentional blank paragraphs
  use 0.5em text with line-height 1, reducing each gap from a full 1.5em line to
  half a line. Ordinary text line-height and unrelated wrapper spacing remain
  unchanged.
- IBM Plex Sans uses regular 300 instead of 200, and emphasis 500 instead of
  300, including real italic faces. These are static instances of the bundled
  variable font, not synthesized bold. The website/standard edition is unchanged.
- Choi Handwriting is enlarged by 15%; Crimson Old Style by 10%. Bold keeps
  the surrounding text size.
- Explicit alignment is applied directly to paragraphs and inherited by their
  descendants, with nested explicit alignment taking precedence. Enable
  **publisher defaults** in the Legacy's text settings to test fonts/alignment.
  Reader overrides can still take precedence over book formatting.
- Scares share their chapter's spine file. CSS 2 `page-break-before/after:
  always` isolates the scare within that file; blank lines only place its
  contents vertically and cannot reliably force a page boundary by themselves.
  Segment-local heading/footnote anchors are namespaced before joining. All
  segment footnotes are collected into one section after the entire chapter,
  outside every scare wrapper. Previously the files were joined but their notes
  were still rendered at segment boundaries.
  The builder estimates scare height from
  text length, character widths, font sizes, paragraphs, explicit breaks, and
  bitmap height, then inserts nonbreaking-space lines with actual `<br />`
  elements before short, centered content. Text scares with at least 120 visible
  characters never get a calculated leading spacer, even when they fit on one
  page. It also adds no spacer when content fills/overflows the usable page.
  Scare illustrations are centered horizontally and vertically in a white
  540 × 700px bitmap canvas, so their placement does not depend on image-centering
  CSS. Smaller authored widths are applied before the canvas is composed. Plain
  figure credits are drawn below the centered artwork and retained as image
  metadata; linked captions and footnotes remain live XHTML. Footnotes now
  appear only in the chapter-end section.
- Images, including those tagged **Official Illustration**, remain complete
  bitmaps scaled proportionally to fit both the 540px text column and 700px page
  height. Tall artwork is reduced to fit its height, never sliced or cropped.
  Only official credit captions are removed. Non-official plain credits are
  composed into the same bitmap as their illustration, with image height
  reduced to reserve room for the credit. This applies inside and outside
  scares. Linked credits retain live XHTML in a break-avoiding figure, with
  image height reduced by the estimated caption height first.
  Authored percentage widths use the available Legacy column.
  Authored pixel widths scale from the website reader's 800px baseline:
  `400px` becomes `270px` on a 540px column. Existing smaller source bitmaps are
  never enlarged. Scare-image canvases apply this sizing before centering.
- The diagnostic includes actual bare/black/Braun boxes, unboxed alternatives,
  colors/fades, image centering and footnote references both inside and outside
  scares. Its one combined endnote section follows all diagnostic content.

The book title includes `(Legacy)`, with a separate Legacy identifier; the
diagnostic is titled `Legacy Formatting Check`. Previously transferred v11
files remain unchanged. Reopen the Legacy edition after a newly requested
build to avoid comparing cached pages from an earlier edition.

Scare centering is approximate in a reflowable book. The default estimate assumes
18px reading text and a 1.5 line-height ratio. To calibrate after a device test:

```sh
python3 scripts/build_new_epub.py --testpage --variant legacy --legacy-font-size 22 --legacy-page-height 680 --no-fetch-twitter
```

`--legacy-font-size` changes the spacing estimate, not the Legacy's reading setting.
`--legacy-page-height` and `--legacy-page-width` also change bitmap bounds. Increasing
the estimated font size or reducing usable height generally produces fewer
leading blank lines. Test at the same Legacy text size you use for reading.

Run compatibility regression checks with:

```sh
python3 scripts/Testing/test_epub_legacy.py --no-epub -v
```

### Website window review for OPS 2.0.1

The [OPS 2.0.1 property table](https://idpf.org/epub/20/spec/OPS_2.0_latest.htm#Section3.3)
lists block display, border, padding, alignment, colors and page-break controls.
The following adaptations use those properties. Only the original plain-window
experiment has been confirmed on the device; the new variants remain available
for device testing in the diagnostic book.

| Website window | Legacy adaptation |
| --- | --- |
| `bare-window` | White rectangle, thin black border, centered text. |
| `black-window` | Black background, white centered text, thin gray border. |
| `braun-screen` | Black screen, pure white centered VCR text at 2em, a thick gray frame, and two lines of internal padding. |
| All other windows | Plaintext presentation; retain typography, markers and spacing, without box borders or backgrounds. |

Bare/black boxes have one line of padding inside; Braun has two. All three
have one blank line outside. The original test box was successful on the Legacy; the revised spacing
and other changes remain available for device testing.

Builds are local only. Do not transfer them to the Legacy without a new explicit
request from the user.

## Gradual sizing and pagination

The remaining notes describe the standard edition.

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

## Build control

Do not build EPUB archives or transfer them to a device unless explicitly requested.
For code-only checks, run the compatibility suite without its archive-building
integration test; the variant routing tests mock the writer and create no EPUBs.
