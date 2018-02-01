+++
author = "Colin Benner"
date = "{{now}}"
description = "A brief analysis of my book collection"
title = "Library statistics"
+++

{{#with stats}}My library currently contains a total of {{all.works}} pieces of writing (novels,
novellas, short stories, text books, etc.) with an estimated {{all.pages}} pages.
These contain more then {{all.words}} words.  That includes the number of words
in works which can be easily counted, e.g. EPUB files, and unreliable –
mostly too low – word counts of PDF or DJVU files.

Of these I have read

  * {{read_long.works}} books, {{read_long.pages}} pages, {{read_long.words}} in total;
  * {{eng_read_long.works}} books, {{eng_read_long.pages}} pages, {{eng_read_long.words}} words in English;
  * {{deu_read_long.works}} books, {{deu_read_long.pages}} pages, {{deu_read_long.words}} words in German; and
  * {{eng_read_short.works}}{{/with}} works of less than {{min_words}} words and less than {{min_pages}} pages in English,
    totalling {{#with stats}}{{eng_read_short.pages}} pages, and {{eng_read_short.words}} words.

Thus, in total, I have read {{read.works}} works consisting of {{read.pages}} pages and {{read.words}} words.{{/with}}
