export const readerState = $state({
  ch_meta: {
    title: "",
    slug: 0,
    category: "",
    index: 0,
    section: "",
    discussion: 0,
    description: ""
  },
  refPanelOpen: false,
  footnotes: "",
  altTextSelections: {} as Record<string, string>,
});
