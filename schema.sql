PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS books (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  owner TEXT NOT NULL DEFAULT 'NILS',
  author TEXT,
  title TEXT NOT NULL,
  publisher TEXT,
  publication_date TEXT,
  language TEXT,
  isbn10 TEXT,
  isbn13 TEXT,
  barcode TEXT,
  series TEXT,
  volume TEXT,
  edition TEXT,
  format TEXT,
  tags TEXT,
  read INTEGER NOT NULL DEFAULT 0,
  kept_after_reading INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_books_title  ON books(title);
CREATE INDEX IF NOT EXISTS idx_books_author ON books(author);
CREATE INDEX IF NOT EXISTS idx_books_isbn13 ON books(isbn13);
CREATE INDEX IF NOT EXISTS idx_books_barcode ON books(barcode);
CREATE INDEX IF NOT EXISTS idx_books_owner   ON books(owner);

CREATE TRIGGER IF NOT EXISTS trg_books_updated
AFTER UPDATE ON books
FOR EACH ROW
BEGIN
  UPDATE books SET updated_at = datetime('now') WHERE id = OLD.id;
END;
CREATE UNIQUE INDEX IF NOT EXISTS uniq_book
ON books(owner, author, title);

