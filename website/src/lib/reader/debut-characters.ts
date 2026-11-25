export interface DebutCharacterAlt {
  id: string;
  name: string;
  nicknames?: string[];
  birthday?: string | null;
  mbti?: string | null;
  firstNovelChapter?: number | null;
  manwhaImage: string | null;
  webnovelImage: string | null;
}

export interface DebutCharacter {
  id: string;
  name: string;
  nicknames?: string[];
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
  {"id": "ParkMoondae", "name": "Park Moondae", "nicknames": ["MoondaeMoondae", "MoonPuppy", "Moondaengdaeng", "Gommeo", "MoonDog", "AI Puppy", "Soft Bean Rice Cake Apple Rice Cake Puppy"], "birthday": "December 15", "mbti": "INTJ", "group": "TeSTAR", "groupRole": "Member", "firstNovelChapter": 1, "manwhaImage": "/debut-characters/ParkMoondaeManhwa.webp", "webnovelImage": "/debut-characters/ParkMoondaeWebnovel.webp", "alts": [{"id": "Ryu-Gunwoo", "name": "Ryu Gunwoo (Original Identity)", "birthday": "December 8", "mbti": "INTJ", "firstNovelChapter": 1, "manwhaImage": "/debut-characters/Ryu-GunwooManhwa.webp", "webnovelImage": null}]},
  {"id": "LeeSejin", "name": "Lee Sejin (Keun Sejin)", "nicknames": ["Big Sejin", "Lee Sejin B", "Haribo", "Gummy Bear", "Sweetest Melon"], "birthday": "August 1", "mbti": "ENTJ", "group": "TeSTAR", "groupRole": "Member", "firstNovelChapter": 3, "manwhaImage": "/debut-characters/LeeSejinManhwa.webp", "webnovelImage": "/debut-characters/LeeSejinWebnovel.webp", "alts": []},
  {"id": "SeonAhyeon", "name": "Seon Ahyeon", "nicknames": ["Angel", "Bambi", "Flower Deer", "Elk", "AhyeonAhyeon", "Disney Prince"], "birthday": "May 7", "mbti": "ISFJ", "group": "TeSTAR", "groupRole": "Member", "firstNovelChapter": 5, "manwhaImage": "/debut-characters/SeonAhyeonManhwa.webp", "webnovelImage": "/debut-characters/SeonAhyeonWebnovel.webp", "alts": []},
  {"id": "ChaEugene", "name": "Cha Eugene", "nicknames": ["Eugene Ignacio Cha", "Cha Kitty", "Cali Boy"], "birthday": "March 6", "mbti": "ENTP", "group": "TeSTAR", "groupRole": "Member", "firstNovelChapter": 6, "manwhaImage": "/debut-characters/ChaEugeneManhwa.webp", "webnovelImage": "/debut-characters/ChaEugeneWebnovel.webp", "alts": []},
  {"id": "KimRaebin", "name": "Kim Raebin", "nicknames": ["Kim Rabbit", "Filial Piety Rabbit", "Medieval Rabbit", "Kim Rap"], "birthday": "November 11", "mbti": "INFP", "group": "TeSTAR", "groupRole": "Member", "firstNovelChapter": 6, "manwhaImage": "/debut-characters/KimRaebinManhwa.webp", "webnovelImage": "/debut-characters/KimRaebinWebnovel.webp", "alts": []},
  {"id": "RyuChungwoo", "name": "Ryu Chungwoo", "nicknames": ["Ryu Cheongwoo"], "birthday": "October 28", "mbti": "ESFJ", "group": "TeSTAR", "groupRole": "Member", "firstNovelChapter": 6, "manwhaImage": "/debut-characters/RyuChungwooManhwa.webp", "webnovelImage": "/debut-characters/RyuChungwooWebnovel.webp", "alts": []},
  {"id": "BaeSejin", "name": "Bae Sejin", "nicknames": ["Lee Sejin A", "Little Sejin", "Hard-working Hamster"], "birthday": "February 7", "mbti": "ISFP", "group": "TeSTAR", "groupRole": "Member", "firstNovelChapter": 6, "manwhaImage": "/debut-characters/BaeSejinManhwa.webp", "webnovelImage": "/debut-characters/BaeSejinWebnovel.webp", "alts": []},
  {"id": "Cheongryeo", "name": "Cheongryeo (Shin Jaehyeon)", "nicknames": ["Shin Jaehyun"], "birthday": "November 27", "mbti": "ISTJ", "group": "VTIC", "groupRole": "Member", "firstNovelChapter": 49, "manwhaImage": "/debut-characters/CheongryeoManhwa.webp", "webnovelImage": "/debut-characters/CheongryeoWebnovel.webp", "alts": []},
  {"id": "Keundal", "name": "Keundal (Park Moondae)", "nicknames": ["Big Moon"], "birthday": "December 15", "mbti": "—", "group": "", "groupRole": "Major Supporting Character", "firstNovelChapter": 252, "manwhaImage": "/debut-characters/Original-Park-MoondaeManhwa.webp", "webnovelImage": null, "alts": [{"id": "RyuGunwoo", "name": "Keundal (Ryu Gunwoo's Body)", "nicknames": ["Big Moon"], "birthday": "December 8", "mbti": null, "firstNovelChapter": 323, "manwhaImage": null, "webnovelImage": "/debut-characters/KeundalWebnovel.webp"}]},
  {"id": "ChoiWongil", "name": "Choi Wongil", "birthday": "Not confirmed", "mbti": "—", "group": "", "groupRole": "Contestant", "firstNovelChapter": 3, "manwhaImage": "/debut-characters/ChoiWongilManhwa.webp", "webnovelImage": null, "alts": []},
  {"id": "Youngrin", "name": "Youngrin", "birthday": "Not confirmed", "mbti": "—", "group": "Saint U", "groupRole": "Judge", "firstNovelChapter": 4, "manwhaImage": "/debut-characters/YoungrinManhwa.webp", "webnovelImage": null, "alts": []},
  {"id": "HaIljoon", "name": "Ha Iljoon (Gold 1)", "birthday": "Not confirmed", "mbti": "—", "group": "", "groupRole": "Contestant", "firstNovelChapter": 11, "manwhaImage": "/debut-characters/HaIljoonManhwa.webp", "webnovelImage": null, "alts": []},
  {"id": "KwonHeeseung", "name": "Kwon Heeseung (Gold 2)", "birthday": "Not confirmed", "mbti": "—", "group": "", "groupRole": "Contestant", "firstNovelChapter": 11, "manwhaImage": "/debut-characters/KwonHeeseungManhwa.webp", "webnovelImage": null, "alts": []},
  {"id": "KimYeonjoo", "name": "Kim Yeonjoo", "nicknames": ["FullMoon Baby (fansite)", "Jiwon (fan account)"], "birthday": "Not confirmed", "mbti": "—", "group": "", "groupRole": "Fansite Master", "firstNovelChapter": 14, "manwhaImage": "/debut-characters/KimYeonjooManhwa.webp", "webnovelImage": null, "alts": []},
  {"id": "MinJunghoon", "name": "Min Junghoon", "birthday": "Not confirmed", "mbti": "—", "group": "", "groupRole": "Contestant", "firstNovelChapter": 26, "manwhaImage": "/debut-characters/MinJunghoonManhwa.webp", "webnovelImage": null, "alts": []},
  {"id": "Jiwon", "name": "Jiwon", "nicknames": ["Kim Raebin's fan", "The college student"], "birthday": "Not confirmed", "mbti": "—", "group": "", "groupRole": "Fan", "firstNovelChapter": 30, "manwhaImage": "/debut-characters/JiwonManhwa.webp", "webnovelImage": null, "alts": []},
  {"id": "Minso", "name": "Minso", "nicknames": ["University Student", "Graduate Student"], "birthday": "Not confirmed", "mbti": "—", "group": "", "groupRole": "Fan", "firstNovelChapter": 30, "manwhaImage": "/debut-characters/MinsoManhwa.webp", "webnovelImage": null, "alts": []},
  {"id": "Sinoh", "name": "Sinoh", "nicknames": ["Oh Yoonsin", "Oh Yunshin", "Shino", "Sino"], "birthday": "September 26", "mbti": "ISFP", "group": "VTIC", "groupRole": "Member", "firstNovelChapter": 50, "manwhaImage": "/debut-characters/SinohManhwa.webp", "webnovelImage": null, "alts": []},
  {"id": "Chaeyul", "name": "Jin Chaeyul", "birthday": "April 10", "mbti": "ESFP", "group": "VTIC", "groupRole": "Member", "firstNovelChapter": 136, "manwhaImage": "/debut-characters/ChaeyulManhwa.webp", "webnovelImage": null, "alts": []},
  {"id": "Kongi", "name": "Kongi", "birthday": "Not confirmed", "mbti": "—", "group": "", "groupRole": "Cheongryeo's Dog", "firstNovelChapter": 195, "manwhaImage": null, "webnovelImage": "/debut-characters/KongiWebnovel.webp", "alts": []},
  {"id": "Judan", "name": "Judan", "nicknames": ["Jung Woodan"], "birthday": "February 16", "mbti": "INTP", "group": "VTIC", "groupRole": "Member", "firstNovelChapter": 287, "manwhaImage": "/debut-characters/JudanManhwa.webp", "webnovelImage": null, "alts": []},
  {"id": "Beehan", "name": "Beehan", "nicknames": ["Choi Taejun", "Club main vocal", "Nightclub guy"], "birthday": "Not confirmed", "mbti": "—", "group": "VTIC", "groupRole": "Member", "firstNovelChapter": 383, "manwhaImage": "/debut-characters/BeehanManhwa.webp", "webnovelImage": null, "alts": []},
];
