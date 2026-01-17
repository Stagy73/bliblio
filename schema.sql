DROP TABLE IF EXISTS books;

CREATE TABLE books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    owner TEXT NOT NULL,
    category TEXT NOT NULL,
    author TEXT NOT NULL,
    title TEXT NOT NULL,
    language TEXT,
    read INTEGER DEFAULT 0,
    kept INTEGER DEFAULT 0,
    publisher TEXT,
    UNIQUE(owner, category, author, title)
);
