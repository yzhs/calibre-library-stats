SELECT
  title,
  ifnull({started}.value, 'NA') AS started,
  ifnull({finished}.value, 'NA') AS finished,
  ({shelf}.value = 'Fiction') AS isfiction,
  ifnull({words}.value, 0) AS words
FROM books
LEFT OUTER JOIN {words} ON {words}.book = books.id
JOIN {shelf}
JOIN {shelf_book_link} ON {shelf}.id = {shelf_book_link}.value AND {shelf_book_link}.book = books.id
JOIN {started} ON {started}.book = books.id
LEFT OUTER JOIN {finished} ON {finished}.book = books.id
WHERE {shelf}.value = 'Fiction' OR {shelf}.value = 'Nonfiction'

UNION

SELECT
  title,
  ifnull({started}.value, 'NA') AS started,
  ifnull({finished}.value, 'NA') AS finished,
  ({shelf}.value = 'Fiction') AS isfiction,
  ifnull({words}.value, 0) AS words
FROM books
LEFT OUTER JOIN {words} ON {words}.book = books.id
JOIN {shelf}
JOIN {shelf_book_link} ON {shelf}.id = {shelf_book_link}.value AND {shelf_book_link}.book = books.id
JOIN {finished} ON {finished}.book = books.id
LEFT OUTER JOIN {started} ON {started}.book = books.id
WHERE {shelf}.value = 'Fiction' OR {shelf}.value = 'Nonfiction'
