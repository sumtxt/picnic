CREATE TABLE IF NOT EXISTS subscribers (
  id              TEXT PRIMARY KEY,
  email           TEXT UNIQUE NOT NULL,
  token           TEXT UNIQUE NOT NULL,
  confirmed       INTEGER NOT NULL DEFAULT 0,
  created_at      TEXT NOT NULL,
  last_sent_week  TEXT
);

CREATE TABLE IF NOT EXISTS journal_preferences (
  subscriber_id TEXT NOT NULL REFERENCES subscribers(id) ON DELETE CASCADE,
  journal_id    TEXT NOT NULL,
  PRIMARY KEY (subscriber_id, journal_id)
);

CREATE TABLE IF NOT EXISTS preprint_preferences (
  subscriber_id TEXT NOT NULL REFERENCES subscribers(id) ON DELETE CASCADE,
  osf_category  TEXT NOT NULL,
  PRIMARY KEY (subscriber_id, osf_category)
);

CREATE INDEX IF NOT EXISTS idx_subscribers_email ON subscribers(email);
CREATE INDEX IF NOT EXISTS idx_subscribers_token ON subscribers(token);
