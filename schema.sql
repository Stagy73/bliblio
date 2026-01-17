CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    owner TEXT,          -- CAROLE / NILS / AXEL
    category TEXT,       -- Livre / BD
    author TEXT,
    title TEXT,
    language TEXT,
    read INTEGER,
    kept INTEGER,
    publisher TEXT
);
