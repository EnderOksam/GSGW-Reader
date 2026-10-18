import type { CommentRow } from "./db";
import type { ReactionAgg, ReactionJoinRow } from "./reactions";

interface CommentReactionRow extends ReactionJoinRow {
  comment_id: number;
}

export function serializeComments(rows: CommentRow[], reactions: CommentReactionRow[], currentUserId: number | null) {
  const byComment = new Map<number, ReactionAgg[]>();
  for (const r of reactions) {
    let list = byComment.get(r.comment_id);
    if (!list) {
      list = [];
      byComment.set(r.comment_id, list);
    }
    let agg = list.find((x) => x.emoji === r.emoji);
    if (!agg) {
      agg = { emoji: r.emoji, count: 0, mine: false, users: [] };
      list.push(agg);
    }
    agg.count += 1;
    if (r.user_id === currentUserId) agg.mine = true;
    const name = r.display_name || r.login;
    if (agg.users.length < 12) agg.users.push(name);
  }

  return rows.map((row) => ({
    id: row.id,
    chapter: row.chapter,
    parentId: row.parent_id,
    body: row.body,
    isLegacy: row.is_legacy === 1,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
    edited: row.edited === 1,
    author: {
      id: row.user_id,
      login: row.login,
      displayName: row.display_name || row.login,
      avatarUrl: row.avatar_url,
      provider: row.provider,
      isLegacy: row.user_is_legacy === 1,
    },
    reactions: byComment.get(row.id) ?? [],
  }));
}
