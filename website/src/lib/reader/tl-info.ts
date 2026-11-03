export interface TLInfo {
  name: string;
  desc: string;
  icon: string;
  color: string;
}

const GSGW_TL_INFO: TLInfo[] = [
  {
    name: "FanTL",
    desc: "This is the recommended translation, with all the features and formatting made specifically for the site.",
    icon: "mdi:star-outline",
    color: "text-yellow-500",
  },
  {
    name: "UnformattedTL",
    desc: "The base story with no special features — equivalent of reading an epub. Once chapters here get formatted they get put under FanTL.",
    icon: "mdi:book-outline",
    color: "text-blue-400",
  },
  {
    name: "MTL",
    desc: "Currently released Part 3 chapters, translated by ZestysDaddy on Discord. Kept separate because adding them to FanTL would disrupt the chapter order by jumping to Part 3 while Part 2 is not yet fully formatted.",
    icon: "mdi:auto-fix",
    color: "text-purple-400",
  },
];

const DEBUT_TL_INFO: TLInfo[] = [
  {
    name: "DEBUTFORMATTED",
    desc: "This is the recommended translation, with all the features and formatting made specifically for the site.",
    icon: "mdi:star-outline",
    color: "text-yellow-500",
  },
  {
    name: "DEBUTPLAINTXT",
    desc: "The base story without any special features or formatting — essentially equivalent to reading an EPUB. Once chapters here are formatted, they are moved to DEBUTFORMATTED.",
    icon: "mdi:book-outline",
    color: "text-blue-400",
  },
];

export function getTLInfo(book: string): TLInfo[] {
  if (book === "debut") return DEBUT_TL_INFO;
  return GSGW_TL_INFO;
}
