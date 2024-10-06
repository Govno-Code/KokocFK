CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    is_admin INTEGER DEFAULT 0,
    time INTEGER NOT NULL
);


CREATE TABLE IF NOT EXISTS news (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    image_url TEXT NOT NULL,
    short_description TEXT NOT NULL,
    category TEXT NOT NULL,
    date TEXT NOT NULL,
    full_text TEXT NOT NULL,
    time INTEGER NOT NULL
);