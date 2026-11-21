export interface DebutCharacterAlt {
  id: string;
  name: string;
  birthday?: string | null;
  mbti?: string | null;
  manwhaImage: string | null;
  webnovelImage: string | null;
}

export interface DebutCharacter {
  id: string;
  name: string;
  birthday: string;
  mbti: string;
  group: string;
  groupRole: string;
  firstNovelChapter: number | null;
  manwhaImage: string | null;
  webnovelImage: string | null;
  alts: DebutCharacterAlt[];
}

export const debutCharacters: DebutCharacter[] = [
  {"id": "ParkMoondae", "name": "Park Moondae", "birthday": "December 15", "mbti": "INTJ", "group": "TeSTAR", "groupRole": "Member", "firstNovelChapter": 1, "manwhaImage": "/debut-characters/ParkMoondaeManwha.webp", "webnovelImage": null, "alts": [{"id": "ryu-gunwoo", "name": "Ryu Gunwoo", "birthday": "December 8", "mbti": "INTJ", "manwhaImage": null, "webnovelImage": null}]},
  {"id": "BaeSejin", "name": "Bae Sejin", "birthday": "February 7", "mbti": "ISFP", "group": "TeSTAR", "groupRole": "Member", "firstNovelChapter": 6, "manwhaImage": "/debut-characters/BaeSejinManwha.webp", "webnovelImage": null, "alts": []},
  {"id": "RyuChungwoo", "name": "Ryu Chungwoo", "birthday": "October 28", "mbti": "ESFJ", "group": "TeSTAR", "groupRole": "Member", "firstNovelChapter": 6, "manwhaImage": "/debut-characters/RyuChungwooManwha.webp", "webnovelImage": null, "alts": []},
  {"id": "SeonAhyeon", "name": "Seon Ahyeon", "birthday": "May 7", "mbti": "ISFJ", "group": "TeSTAR", "groupRole": "Member", "firstNovelChapter": 5, "manwhaImage": "/debut-characters/SeonAhyeonManwha.webp", "webnovelImage": null, "alts": []},
  {"id": "LeeSejin", "name": "Lee Sejin", "birthday": "August 1", "mbti": "ENTJ", "group": "TeSTAR", "groupRole": "Member", "firstNovelChapter": 3, "manwhaImage": "/debut-characters/LeeSejinManwha.webp", "webnovelImage": null, "alts": []},
  {"id": "ChaEugene", "name": "Cha Eugene", "birthday": "March 6", "mbti": "ENTP", "group": "TeSTAR", "groupRole": "Member", "firstNovelChapter": 9, "manwhaImage": "/debut-characters/ChaEugeneManwha.webp", "webnovelImage": null, "alts": []},
  {"id": "KimRaebin", "name": "Kim Raebin", "birthday": "November 11", "mbti": "INFP", "group": "TeSTAR", "groupRole": "Member", "firstNovelChapter": 20, "manwhaImage": "/debut-characters/KimRaebinManwha.webp", "webnovelImage": null, "alts": []},
  {"id": "Cheongryeo", "name": "Cheongryeo", "birthday": "November 27", "mbti": "ISTJ", "group": "VTIC", "groupRole": "Member", "firstNovelChapter": 49, "manwhaImage": null, "webnovelImage": null, "alts": []},
  {"id": "Keundal", "name": "Keundal", "birthday": "December 15 (December 8)", "mbti": "Not confirmed", "group": "Supporting cast", "groupRole": "Major supporting character", "firstNovelChapter": 252, "manwhaImage": null, "webnovelImage": null, "alts": []},
];
