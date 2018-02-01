+++
author = "Colin Benner"
date = "{{now}}"
description = "A brief analysis of my book collection"
title = "Library statistics"
+++

{{#with stats}}My library currently contains a total of {{group-digits all.works}} pieces of writing (novels,
novellas, short stories, text books, etc.) with an estimated {{group-digits all.pages}} pages.
These contain more then {{group-digits all.words}} words.  That includes the number of words
in works which can be easily counted, e.g. EPUB files, and unreliable –
mostly too low – word counts of PDF or DJVU files.

Of these I have read

  * {{group-digits read_long.works}} books, {{group-digits read_long.pages}} pages, {{group-digits read_long.words}} in total;
  * {{group-digits eng_read_long.works}} books, {{group-digits eng_read_long.pages}} pages, {{group-digits eng_read_long.words}} words in English;
  * {{group-digits deu_read_long.works}} books, {{group-digits deu_read_long.pages}} pages, {{group-digits deu_read_long.words}} words in German; and
  * {{group-digits eng_read_short.works}}{{/with}} works of less than {{group-digits min_words}} words and less than {{group-digits min_pages}} pages in English,
    totalling {{#with stats}}{{group-digits eng_read_short.pages}} pages, and {{group-digits eng_read_short.words}} words.

Thus, in total, I have read {{group-digits read.works}} works consisting of {{group-digits read.pages}} pages and {{group-digits read.words}} words.{{/with}}
