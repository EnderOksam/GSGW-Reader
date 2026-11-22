export interface DebutCharacterAlt {
  id: string;
  name: string;
  birthday?: string | null;
  mbti?: string | null;
  firstNovelChapter?: number | null;
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
  {"id": "ParkMoondae", "name": "Park Moondae", "birthday": "December 15", "mbti": "INTJ", "group": "TeSTAR", "groupRole": "Member", "firstNovelChapter": 1, "manwhaImage": "/debut-characters/ParkMoondaeManwha.webp", "webnovelImage": "/debut-characters/ParkMoondaeWebnovel.webp", "alts": [{"id": "Ryu-Gunwoo", "name": "Ryu Gunwoo (Original Identity)", "birthday": "December 8", "mbti": "INTJ", "firstNovelChapter": 1, "manwhaImage": "/debut-characters/Ryu-GunwooManhwa.webp", "webnovelImage": null}]},
  {"id": "LeeSejin", "name": "Lee Sejin (Keun Sejin)", "birthday": "August 1", "mbti": "ENTJ", "group": "TeSTAR", "groupRole": "Member", "firstNovelChapter": 3, "manwhaImage": "/debut-characters/LeeSejinManwha.webp", "webnovelImage": "/debut-characters/LeeSejinWebnovel.webp", "alts": []},
  {"id": "SeonAhyeon", "name": "Seon Ahyeon", "birthday": "May 7", "mbti": "ISFJ", "group": "TeSTAR", "groupRole": "Member", "firstNovelChapter": 5, "manwhaImage": "/debut-characters/SeonAhyeonManwha.webp", "webnovelImage": "/debut-characters/SeonAhyeonWebnovel.webp", "alts": []},
  {"id": "BaeSejin", "name": "Bae Sejin (Lee Sejin A)", "birthday": "February 7", "mbti": "ISFP", "group": "TeSTAR", "groupRole": "Member", "firstNovelChapter": 6, "manwhaImage": "/debut-characters/BaeSejinManwha.webp", "webnovelImage": "/debut-characters/BaeSejinWebnovel.webp", "alts": []},
  {"id": "RyuChungwoo", "name": "Ryu Chungwoo", "birthday": "October 28", "mbti": "ESFJ", "group": "TeSTAR", "groupRole": "Member", "firstNovelChapter": 6, "manwhaImage": "/debut-characters/RyuChungwooManwha.webp", "webnovelImage": "/debut-characters/RyuChungwooWebnovel.webp", "alts": []},
  {"id": "ChaEugene", "name": "Cha Eugene", "birthday": "March 6", "mbti": "ENTP", "group": "TeSTAR", "groupRole": "Member", "firstNovelChapter": 9, "manwhaImage": "/debut-characters/ChaEugeneManwha.webp", "webnovelImage": "/debut-characters/ChaEugeneWebnovel.webp", "alts": []},
  {"id": "KimRaebin", "name": "Kim Raebin", "birthday": "November 11", "mbti": "INFP", "group": "TeSTAR", "groupRole": "Member", "firstNovelChapter": 20, "manwhaImage": "/debut-characters/KimRaebinManwha.webp", "webnovelImage": "/debut-characters/KimRaebinWebnovel.webp", "alts": []},
  {"id": "Cheongryeo", "name": "Shin Jaehyeon (Cheongryeo)", "birthday": "November 27", "mbti": "ISTJ", "group": "VTIC", "groupRole": "Member", "firstNovelChapter": 49, "manwhaImage": "/debut-characters/CheongryeoManwha.webp", "webnovelImage": "/debut-characters/CheongryeoWebnovel.webp", "alts": []},
  {"id": "Keundal", "name": "Keundal (Park Moondae)", "birthday": "December 15", "mbti": "—", "group": "", "groupRole": "Major Supporting Character", "firstNovelChapter": 252, "manwhaImage": "/debut-characters/Original-Park-MoondaeManwha.webp", "webnovelImage": null, "alts": [{"id": "RyuGunwoo", "name": "Ryu Gunwoo (Current Body)", "birthday": "December 8", "mbti": null, "firstNovelChapter": 323, "manwhaImage": null, "webnovelImage": "/debut-characters/KeundalWebnovel.webp"}]},
  {"id": "ChoiWongil", "name": "Choi Wongil", "birthday": "Not confirmed", "mbti": "—", "group": "", "groupRole": "Contestant", "firstNovelChapter": 3, "manwhaImage": "/debut-characters/ChoiWongilManwha.webp", "webnovelImage": null, "alts": []},
  {"id": "Youngrin", "name": "Youngrin", "birthday": "Not confirmed", "mbti": "—", "group": "Saint U", "groupRole": "Judge", "firstNovelChapter": 4, "manwhaImage": "/debut-characters/YoungrinManwha.webp", "webnovelImage": null, "alts": []},
  {"id": "HaIljoon", "name": "Ha Iljoon", "birthday": "Not confirmed", "mbti": "—", "group": "", "groupRole": "Contestant", "firstNovelChapter": 11, "manwhaImage": "/debut-characters/HaIljoonManwha.webp", "webnovelImage": null, "alts": []},
  {"id": "KwonHeeseung", "name": "Kwon Heeseung", "birthday": "Not confirmed", "mbti": "—", "group": "", "groupRole": "Contestant", "firstNovelChapter": 11, "manwhaImage": "/debut-characters/KwonHeeseungManwha.webp", "webnovelImage": null, "alts": []},
  {"id": "KimYeonjoo", "name": "Kim Yeonjoo", "birthday": "Not confirmed", "mbti": "—", "group": "", "groupRole": "Fansite Master", "firstNovelChapter": 14, "manwhaImage": "/debut-characters/KimYeonjooManwha.webp", "webnovelImage": null, "alts": []},
  {"id": "MinJunghoon", "name": "Min Junghoon", "birthday": "Not confirmed", "mbti": "—", "group": "", "groupRole": "Contestant", "firstNovelChapter": 26, "manwhaImage": "/debut-characters/MinJunghoonManwha.webp", "webnovelImage": null, "alts": []},
  {"id": "Jiwon", "name": "Jiwon", "birthday": "Not confirmed", "mbti": "—", "group": "", "groupRole": "Fan", "firstNovelChapter": 30, "manwhaImage": "/debut-characters/JiwonManwha.webp", "webnovelImage": null, "alts": []},
  {"id": "Minso", "name": "Minso", "birthday": "Not confirmed", "mbti": "—", "group": "", "groupRole": "Fan", "firstNovelChapter": 30, "manwhaImage": "/debut-characters/MinsoManwha.webp", "webnovelImage": null, "alts": []},
  {"id": "Sinoh", "name": "Sinoh", "birthday": "September 26", "mbti": "ISFP", "group": "VTIC", "groupRole": "Member", "firstNovelChapter": 50, "manwhaImage": "/debut-characters/SinohManwha.webp", "webnovelImage": null, "alts": []},
  {"id": "Chaeyul", "name": "Chaeyul", "birthday": "April 10", "mbti": "ESFP", "group": "VTIC", "groupRole": "Member", "firstNovelChapter": 136, "manwhaImage": "/debut-characters/ChaeyulManwha.webp", "webnovelImage": null, "alts": []},
  {"id": "Beehan", "name": "Beehan", "birthday": "Not confirmed", "mbti": "—", "group": "VTIC", "groupRole": "Member", "firstNovelChapter": 182, "manwhaImage": "/debut-characters/BeehanManwha.webp", "webnovelImage": null, "alts": []},
  {"id": "Kongi", "name": "Kongi", "birthday": "Not confirmed", "mbti": "—", "group": "", "groupRole": "Cheongryeo's Dog", "firstNovelChapter": 195, "manwhaImage": null, "webnovelImage": "/debut-characters/KongiWebnovel.webp", "alts": []},
  {"id": "Judan", "name": "Judan", "birthday": "February 16", "mbti": "INTP", "group": "VTIC", "groupRole": "Member", "firstNovelChapter": 287, "manwhaImage": "/debut-characters/JudanManwha.webp", "webnovelImage": null, "alts": []},
];
