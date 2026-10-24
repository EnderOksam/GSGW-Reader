CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  provider TEXT NOT NULL,
  provider_user_id TEXT NOT NULL,
  login TEXT NOT NULL,
  display_name TEXT,
  avatar_url TEXT,
  is_legacy INTEGER NOT NULL DEFAULT 0,
  access_token TEXT,
  token_scopes TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  UNIQUE (provider, provider_user_id)
);

CREATE TABLE IF NOT EXISTS comments (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  chapter TEXT NOT NULL,
  user_id INTEGER NOT NULL REFERENCES users (id),
  parent_id INTEGER REFERENCES comments (id),
  body TEXT NOT NULL,
  legacy_id TEXT UNIQUE,
  is_legacy INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT,
  edited INTEGER NOT NULL DEFAULT 0,
  deleted INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_comments_chapter ON comments (chapter);
CREATE INDEX IF NOT EXISTS idx_comments_parent ON comments (parent_id);

CREATE TABLE IF NOT EXISTS reactions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  comment_id INTEGER NOT NULL REFERENCES comments (id),
  user_id INTEGER NOT NULL REFERENCES users (id),
  emoji TEXT NOT NULL,
  legacy_id TEXT UNIQUE,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  UNIQUE (comment_id, user_id, emoji)
);

CREATE INDEX IF NOT EXISTS idx_reactions_comment ON reactions (comment_id);

CREATE TABLE IF NOT EXISTS chapter_reactions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  chapter TEXT NOT NULL,
  user_id INTEGER NOT NULL REFERENCES users (id),
  emoji TEXT NOT NULL,
  legacy_id TEXT UNIQUE,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  UNIQUE (chapter, user_id, emoji)
);

CREATE INDEX IF NOT EXISTS idx_chapter_reactions_chapter ON chapter_reactions (chapter);
