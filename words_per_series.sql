SELECT
  --custom_column_6.value >= 100 OR ifnull(custom_column_5.value, 0) >= 10000 AS is_long,
  languages.lang_code  AS lang,
  custom_column_11.value  AS read,
  COUNT(*) AS works,
  SUM(custom_column_6.value) AS pages,
  SUM(ifnull(custom_column_5.value, 0)) AS words,
  authors.name as author,
  series.name as series
FROM books
JOIN books_languages_link ON books.id = books_languages_link.book
LEFT OUTER JOIN books_series_link    ON books.id = books_series_link.book
JOIN books_authors_link   ON books.id = books_authors_link.book
JOIN languages            ON languages.id = books_languages_link.lang_code
JOIN custom_column_6             ON books.id = custom_column_6.book
LEFT OUTER JOIN custom_column_11 ON books.id = custom_column_11.book
LEFT OUTER JOIN custom_column_5  ON books.id = custom_column_5.book
JOIN authors ON books_authors_link.author = authors.id
LEFT OUTER JOIN series ON books_series_link.series = series.id
group by author, series.name
order by words desc
