+++
author = "Colin Benner"
date = "{{now}}"
description = "A brief analysis of my book collection"
title = "Library statistics"
+++

My library currently contains a total of {{stats.all.works}} pieces of writing (novels, novellas, short stories, text books, etc.) with an estimated {{stats.all.pages}} pages.  These contain more then {{stats.all.words}} words.  That includes the number of words in works which can be easily counted, e.g. EPUB files, and unreliable – mostly too low – word counts of PDF or DJVU files.

Of these I have read

  * {{stats.read_long.works}} books, {{stats.read_long.pages}} pages, {{stats.read_long.words}} in total;
  * {{stats.eng_read_long.works}} books, {{stats.eng_read_long.pages}} pages, {{stats.eng_read_long.words}} words in English;
  * {{stats.deu_read_long.works}} books, {{stats.deu_read_long.pages}} pages, {{stats.deu_read_long.words}} words in German; and
  * {{stats.eng_read_short.works}} works of less than {{min_words}} words and less than {{min_pages}} pages in English, totalling {{stats.eng_read_short.pages}} pages, and {{stats.eng_read_short.words}} words.

Thus, in total, I have read {{stats.read.works}} works consisting of {{stats.read.works}} pages and {{stats.read.works}} words.
