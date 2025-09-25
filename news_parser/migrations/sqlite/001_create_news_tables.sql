PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS sources (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  rss_url TEXT,
  website TEXT,
  created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS articles (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  url TEXT UNIQUE,
  title TEXT,
  body TEXT,
  published_at TEXT,
  source_id INTEGER,
  hash TEXT UNIQUE,
  language TEXT,
  sentiment INTEGER,
  created_at TEXT DEFAULT (datetime('now')),
  FOREIGN KEY(source_id) REFERENCES sources(id)
);

CREATE TABLE IF NOT EXISTS article_ticker (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  article_id INTEGER,
  ticker_id INTEGER,
  mention_text TEXT,
  mention_type TEXT,
  confidence REAL DEFAULT 1.0,
  FOREIGN KEY(article_id) REFERENCES articles(id) ON DELETE CASCADE
);

CREATE VIRTUAL TABLE IF NOT EXISTS articles_fts USING fts5(title, body, content='articles', content_rowid='id');

CREATE TRIGGER IF NOT EXISTS articles_ai AFTER INSERT ON articles BEGIN
  INSERT INTO articles_fts(rowid, title, body) VALUES (new.id, new.title, new.body);
END;
CREATE TRIGGER IF NOT EXISTS articles_ad AFTER DELETE ON articles BEGIN
  DELETE FROM articles_fts WHERE rowid = old.id;
END;
CREATE TRIGGER IF NOT EXISTS articles_au AFTER UPDATE ON articles BEGIN
  UPDATE articles_fts SET title = new.title, body = new.body WHERE rowid = new.id;
END;

CREATE TABLE IF NOT EXISTS jobs_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  job_type TEXT,
  started_at TEXT,
  finished_at TEXT,
  new_articles INTEGER,
  duplicates INTEGER,
  status TEXT,
  log TEXT
);

CREATE TABLE IF NOT EXISTS jobs_lock (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  locked INTEGER DEFAULT 0,
  locked_at TEXT,
  pid INTEGER
);
INSERT OR IGNORE INTO jobs_lock (id, locked) VALUES (1, 0);
