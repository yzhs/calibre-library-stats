using Base.Markdown
using Base.Nullable

using DataFrames
using Formatting
using SQLite

# Open the database
db_file = expanduser("~/books/non-fiction/metadata.db")
db = SQLite.DB(db_file);

# Handle the custom table names properly
current_reading = "custom_column_4";
shelf = "custom_column_7";
goodreads_rating = "custom_column_12";

percent_read = "custom_column_2";
words = "custom_column_5";
pages = "custom_column_6";
fkg = "custom_column_8";
gfi = "custom_column_9";
fre = "custom_column_10";
read = "custom_column_11";

# How many pages an entry has to have to count as a book
min_pages = 100;


#
# Query the database
#

# Compute some totals
total_books = get(SQLite.query(db, "select count(*) from $pages;")[1,1])
total_pages = get(SQLite.query(db, "select sum(value) from $pages;")[1,1])
total_words = get(SQLite.query(db, "select sum(value) from $words;")[1,1])

# Information on works I have read
num_read = get(SQLite.query(db, "select count(*) from $read;")[1,1])


tmp = SQLite.query(db, """select count(*), sum($pages.value), sum($words.value)
from $read
join books_languages_link on($read.book = books_languages_link.book)
join languages on(books_languages_link.lang_code = languages.id)
join books on($read.book = books.id)
join $words on($words.book = books.id)
join $pages on($pages.book = books.id)
where $read.value = 1 and languages.lang_code = "eng" and $pages.value >= $min_pages;""")
english_books = map(get, convert(Array, tmp))

tmp = SQLite.query(db, """select count(*), sum($pages.value), sum($words.value)
from $read
join books_languages_link on($read.book = books_languages_link.book)
join languages on(books_languages_link.lang_code = languages.id)
join books on($read.book = books.id)
join $words on($words.book = books.id)
join $pages on($pages.book = books.id)
where $read.value = 1 and languages.lang_code = "deu" and $pages.value >= $min_pages;""")
german_books = map(get, convert(Array, tmp))

tmp = SQLite.query(db, """select count(*), sum($pages.value), sum($words.value)
from $read
join books_languages_link on($read.book = books_languages_link.book)
join languages on(books_languages_link.lang_code = languages.id)
join books on($read.book = books.id)
join $words on($words.book = books.id)
join $pages on($pages.book = books.id)
where $read.value = 1 and $pages.value < $min_pages;""")
short_texts = map(get, convert(Array, tmp))

total_read = english_books + german_books + short_texts

books = SQLite.query(db, """select books.id, books.title, books.series_index, data.format from books
join data on(books.id == data.book)
join books_languages_link on (books.id = books_languages_link.book)
join languages on(books_languages_link.lang_code = languages.id)
where data.format <> 'ORIGINAL_EPUB';""")

books = DataFrame(id = convert(Array, books[:id]),
  title = convert(Array, books[:title]),
  series_index = convert(Array, books[:series_index]),
  format = convert(Array, books[:format])
)


#
# Generate a simple report
#
f(x) = format(x, commas=true)

tmpl = """My (electronic) library currently contains a total of $total_books
pieces of writing (novels, novellas, short stories, text books, etc.) with an
estimated $(f(total_pages)) pages.  These contain more then $(f(total_words))
words.  That includes the number of words in works which can be easily counted,
e.g.  EPUB files, and unreliable—mostly too low—word counts of PDF or DJVU
files.

Of these I have read

* $(f(english_books[1])) books, $(f(english_books[2])) pages,
$(f(english_books[3])) words in English;
* $(f(german_books[1])) books, $(f(german_books[2])) pages,
$(f(german_books[3])) words in German; and
* $(f(short_texts[1])) works of less than $min_pages pages in either English or
German, totalling $(f(short_texts[2])) pages, and $(f(short_texts[3])) words.

Thus, in total, I have read $(f(total_read[1])) works consisting of
$(f(total_read[2])) pages and $(f(total_read[3])) words.
"""

output = Base.Markdown.parse(tmpl);

file = open(expanduser("~/site/local/content/library.md"), "w")
write(file, """+++
author = "Colin Benner"
date = "2016-07-18T21:56:27+02:00"
description = "A short analysis of my (e)book collection"
title = "Library statistics"
+++

""")
write(file, Base.Markdown.plain(output))
close(file)

display(output)
