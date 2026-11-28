// Please don't remove emojis from ALLOWED_REACTIONS: that requires cleaning D1, so ask me directly first.
// Adding emojis is fine just don't break this line.
export const ALLOWED_REACTIONS = ["👍", "❤️", "😂", "🎉", "😮", "😢", "🔥", "👀", "🚀", "👎", "😭", "🙏", "💯", "🤔"];
export const ALLOWED_REACTION_SET = new Set(ALLOWED_REACTIONS);

export interface ReactionAgg {
  emoji: string;
  count: number;
  mine: boolean;
  users: string[];
}

export interface ReactionJoinRow {
  emoji: string;
  user_id: number;
  display_name: string | null;
  login: string;
}

export function decodeEmojiParam(raw: string): string {
  try {
    return decodeURIComponent(raw);
  } catch {
    return raw;
  }
}

export function aggregateReactions(
  rows: ReactionJoinRow[],
  currentUserId: number | null,
  maxUsers = 12
): ReactionAgg[] {
  const reactions: ReactionAgg[] = [];
  for (const r of rows) {
    let agg = reactions.find((x) => x.emoji === r.emoji);
    if (!agg) {
      agg = { emoji: r.emoji, count: 0, mine: false, users: [] };
      reactions.push(agg);
    }
    agg.count += 1;
    if (currentUserId != null && r.user_id === currentUserId) agg.mine = true;
    if (agg.users.length < maxUsers) agg.users.push(r.display_name || r.login);
  }
  return reactions;
}
