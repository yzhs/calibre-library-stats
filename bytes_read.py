from dataclasses import dataclass
import glob
import os.path
import sqlite3
import sys

con = sqlite3.connect("/home/yzhs/books/library/metadata.db")
cur = con.cursor()

read_table_id = cur.execute('SELECT id FROM custom_columns where name = "Read"').fetchone()[0]
read_table = f"custom_column_{read_table_id}"

read_books = list(cur.execute(f"""
    SELECT title, path
    FROM {read_table}
    JOIN books ON books.id = {read_table}.book
    JOIN books_languages_link ON books_languages_link.book = books.id
    JOIN languages ON languages.id = books_languages_link.lang_code
    WHERE {read_table}.value = 1 AND languages.lang_code = "eng"
""".replace("\n", " ")))
len(read_books)
print(read_books[:10])

@dataclass
class Book:
    title: str
    path: str
    size: int

books = []
for title, path in read_books:
    author = path.split("/")[0]
    full_path = glob.glob(f"/home/yzhs/books/library/{path}/*.txt")
    try:
        size = os.path.getsize(full_path[0])
    except IndexError:
        print("No file matching pattern:", title, file=sys.stderr)
    except FileNotFoundError:
        print("File not found:", full_path, file=sys.stderr)
    books.append(Book(title, path, size))

print(sum(book.size for book in books))
