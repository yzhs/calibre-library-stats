SELECT
  title,
  ifnull({started}.value, 'NA') AS started,
  ifnull({finished}.value, 'NA') AS finished
FROM books
JOIN {started} ON {started}.book = books.id
LEFT OUTER JOIN {finished} ON {finished}.book = books.id

UNION

SELECT
  title,
  ifnull({started}.value, 'NA') AS started,
  ifnull({finished}.value, 'NA') AS finished
FROM books
JOIN {finished} ON {finished}.book = books.id
LEFT OUTER JOIN {started} ON {started}.book = books.id
