SELECT
  custom_column_6.value >= 100 OR ifnull(custom_column_5.value, 0) >= 10000 AS is_long,
  languages.lang_code  AS lang,
  custom_column_11.value  AS read,
  COUNT(*)   AS works,
  SUM(custom_column_6.value) AS pages,
  SUM(ifnull(custom_column_5.value, 0)) AS words,
  datetime(custom_column_13.value) as finished,
  authors.name
FROM books
JOIN books_languages_link ON books.id = books_languages_link.book
JOIN languages            ON languages.id = books_languages_link.lang_code
JOIN custom_column_6              ON books.id = custom_column_6.book
LEFT OUTER JOIN custom_column_11    ON books.id = custom_column_11.book
LEFT OUTER JOIN custom_column_5   ON books.id = custom_column_5.book
JOIN custom_column_13 ON books.id = custom_column_13.book
JOIN books_authors_link ON books.id = books_authors_link.book
JOIN authors ON books_authors_link.author = authors.id
where read is not null
group by authors.name
order by words desc
