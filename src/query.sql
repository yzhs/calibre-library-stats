SELECT
  {pages}.value >= {min_pages} OR ifnull({words}.value, 0) >= {min_words} AS is_long,
  languages.lang_code                                                     AS lang,
  {read}.value                                                            AS read,
  COUNT(*)                                                                AS works,
  SUM({pages}.value)                                                      AS pages,
  SUM(ifnull({words}.value, 0))                                           AS words
FROM books
JOIN books_languages_link ON books.id = books_languages_link.book
JOIN languages            ON languages.id = books_languages_link.lang_code
JOIN {pages}              ON books.id = {pages}.book
LEFT OUTER JOIN {read}    ON books.id = {read}.book
LEFT OUTER JOIN {words}   ON books.id = {words}.book
{condition}
