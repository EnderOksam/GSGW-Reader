import bookData from "$lib/meta.json";

export const prerender = true;

export function entries() {
  return [
    { book: "gsgw" },
    { book: "uder" },
    { book: "debut" },
    { book: "manwha" },
  ];
}

export function load({ params }) {
  const book = params.book ?? "gsgw";
  if (book === "uder") {
    return { records: ((bookData as any).uder?.records ?? []) };
  }
  return { records: [] };
}
