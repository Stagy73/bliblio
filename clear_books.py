import sqlite3

conn = sqlite3.connect("data/books.sqlite")
conn.execute("DELETE FROM books")
conn.commit()
conn.close()

print("✅ Table books vidée")
