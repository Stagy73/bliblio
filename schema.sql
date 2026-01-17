CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    owner TEXT,
    category TEXT,
    author TEXT,
    title TEXT,
    language TEXT,
    read INTEGER,
    kept INTEGER,
    publisher TEXT,
    UNIQUE(owner, author, title)
);