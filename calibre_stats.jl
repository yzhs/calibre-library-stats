using Base.Markdown
using Base.Nullable

using DataFrames
using DataFramesMeta
using Formatting
using SQLite

# Open the database
const db_file = expanduser("~/books/non-fiction/metadata.db")
db = SQLite.DB(db_file);

# TODO Handle the custom table names properly
const current_reading  = "custom_column_4";
const shelf            = "custom_column_15";
const goodreads_rating = "custom_column_12";

const percent_read = "custom_column_2";
const words        = "custom_column_5";
const pages        = "custom_column_6";
const fkg          = "custom_column_8";
const gfi          = "custom_column_9";
const fre          = "custom_column_10";
const read         = "custom_column_11";
const readin       = "custom_column_16";
const readin_link  = "books_custom_column_16_link";

# How many pages an entry has to have to count as a book
const min_words = 10_000;
const min_pages = 100;


#
# Query the database
#
const available_columns = [:books, :pages, :words, :lang, :read, :readin]

const column_map = Dict([(:books, "COUNT(*)"), (:pages, "SUM($pages.value)"),
(:words, "SUM($words.value)"), (:lang, "languages.lang_code"),
(:read, "$read.value"), (:readin, "$readin.value")])

const all_stats   = "COUNT(*), SUM($pages.value), SUM(ifnull($words.value, 0))"
const all_columns = "$all_stats, languages.lang_code, $read.value"

const is_short_work = "($words.value < $min_words OR $words.value IS NULL AND $pages.value < $min_pages)"
const is_long_work = "($words.value >= $min_words OR ($words.value IS NULL AND $pages.value >= $min_pages))"

const is_english  = "languages.lang_code = 'eng'"
const is_german   = "languages.lang_code = 'deu'"

const language = Dict(:all => "All languages", :deu => "German", :eng => "English", :jbo => "lojban")

const default_from = """books
JOIN books_languages_link    ON books.id                       = books_languages_link.book
JOIN languages               ON books_languages_link.lang_code = languages.id
JOIN $pages                  ON books.id                       = $pages.book
LEFT OUTER JOIN $read        ON books.id                       = $read.book
LEFT OUTER JOIN $words       ON books.id                       = $words.book
LEFT OUTER JOIN $readin_link ON books.id                       = $readin_link.book
LEFT OUTER JOIN $readin      ON $readin_link.value             = $readin.id
"""

# Construct a query string and execute the query, returning a dataframe without
# nullable columns
function query(columns   :: Array{Symbol, 1},
               condition :: Union{String, Array{String}},
               group_by  :: Union{String, Array{String}})
  nullable_to_na(x) = isnull(x) ? NA : get(x)
  select = map(x -> column_map[x], columns)

  # Build the query string
  query_string = "SELECT " * join(select, ", ")
  query_string *= " FROM " * default_from
  if !isempty(condition)
    query_string *= " WHERE " *
    if typeof(condition) == String
      condition
    else
      join(condition, " AND ")
    end
  end
  if typeof(group_by) != String
    group_by = join(group_by, ", ")
  end
  if !isempty(group_by)
    query_string *= " GROUP BY " * group_by
  end
  query_string *= " ORDER BY languages.lang_code ASC"

  # and execute the query
  foo = SQLite.query(db, query_string)

  # Polish the resulting DataFrame
  names!(foo, columns)
  for col in columns
    foo[col] = convert(Array, map(nullable_to_na, foo[col]))
  end
  foo
end

query(str::Union{String, Array{String}}) = query(available_columns, str, ["$read.value", "languages.lang_code"])
query() = query(String[])


#
# Actually query the database
#
all_works   = query()
long_works  = query(is_long_work)
short_works = query(is_short_work)

english_books = @where(long_works, :lang .== "eng")
german_books = @where(long_works, :lang .== "deu")


total_books = sum(all_works[:books])
total_pages = sum(all_works[:pages])
total_words = sum(all_works[:words])

read_all_works = @where(all_works, !isna(:read))

#             length  read  language
#               |       |     |
#               v       v     v
works = Dict((:all,   :all, :all) => all_works,
             (:long,  :all, :all) => long_works,
             (:short, :all, :all) => short_works)

all_languages = sort(union(map(x -> convert(Symbol, x), all_works[:lang])))

read_statuses = [:all]

for length in [:all, :long, :short]
    works[(length, :read, :all)] = @where(works[(length, :all, :all)], !isna(:read))
  for lang in all_languages
    works[(length, :all, lang)] = @where(works[(length, :all, :all)], :lang .== string(lang))
    works[(length, :read, lang)] = @where(works[(length, :all, lang)], !isna(:read))
  end
end


read_short_works = @where(short_works, !isna(:read))
read_long_works = long_works[!long_works[:read].na, :]

df = read_long_works
read_english_books = @where(read_long_works, :lang .== "eng", :read .== 1)
read_german_books = @where(read_long_works, :lang .== "deu", :read .== 1)
read_in_german  = @where(read_long_works, (:lang .== "deu") | (:read .== 0))
read_in_german  = DataFrame(books = sum(read_in_german[:books]), pages = sum(read_in_german[:pages]), words = sum(read_in_german[:words]))
read_short_works = DataFrame(books = sum(read_short_works[:books]), pages = sum(read_short_works[:pages]), words = sum(read_short_works[:words]))


total_read = sum(convert(Array, all_works[!all_works[:read].na, [:books, :pages, :words]]), 1)

#books = SQLite.query(db, """select books.id, books.title, books.series_index, data.format from books
#join data on(books.id == data.book)
#join books_languages_link on (books.id = books_languages_link.book)
#join languages on(books_languages_link.lang_code = languages.id)
#where data.format <> 'ORIGINAL_EPUB';""")
#
#books = DataFrame(id = convert(Array, books[:id]),
#  title = convert(Array, books[:title]),
#  series_index = convert(Array, books[:series_index]),
#  format = convert(Array, books[:format])
#)


#
# Generate a simple report
#
# Group digits
f(language::Symbol, length::Symbol) = (read::Symbol, column::Symbol) ->
  format(sum(works[(length, read, language)][column]), commas=true)
f(df::DataFrame, s::Symbol) = format(sum(df[s]), commas=true)
f(x::DataArrays.DataArray) = format(sum(x), commas=true) # TODO make sure there is only one row
f(x::Integer) = format(x, commas=true)

function percent(needle::DataFrame, haystack::DataFrame, column::Symbol)
  return format(sum(needle[column]) * (100.0::Real) / sum(haystack[column]), precision=1) * "%"
end

function render_table(lang::Symbol, length::Symbol)
  if size(works[(length, :read, lang)], 1) == 0
    return ""
  end
  g = f(lang, length)
  percnt(column::Symbol) = percent(works[(length, :read, lang)], works[(length, :all, lang)], column)
  result = ""
  if length == :short
    result *= "### Short Works"
  elseif length == :long
    result *= "### Long Works"
  end
  result * """

  | Status    | Books               | Pages               | Words               |
  | :-------  | ------------------: | ------------------: | ------------------: |
  | All       | $(g(:all, :books))  | $(g(:all, :pages))  | $(g(:all, :words))  |
  | Read      | $(g(:read, :books)) | $(g(:read, :pages)) | $(g(:read, :words)) |
  | *Percent* | *$(percnt(:books))* | *$(percnt(:pages))* | *$(percnt(:words))* |
  """
end

function bullet(language::Symbol)
  "* "
end


tmpl = """My (electronic) library currently contains a total of $total_books
pieces of writing (novels, novellas, short stories, text books, etc.) with an
estimated $(f(total_pages)) pages.  These contain more then $(f(total_words))
words.  That includes the number of words in works which can be easily counted,
e.g.  EPUB files, and unreliable – mostly too low – word counts of PDF or DJVU
files.

Of these I have read

* $(f(read_english_books[:books])) books ($(percent(read_english_books, english_books, :books))),
  $(f(read_english_books[:pages])) pages ($(percent(read_english_books, english_books, :pages))),
  $(f(read_english_books[:words])) words in English ($(percent(read_english_books, english_books, :words)));
* $(f(read_in_german[:books])) books ($(percent(read_german_books, german_books, :books))),
  $(f(read_in_german[:pages])) pages ($(percent(read_german_books, german_books, :pages))),
  $(f(read_in_german[:words])) words in German ($(percent(read_german_books, german_books, :words)));
  and
* $(f(read_short_works[:books])) works ($(percent(read_short_works, short_works, :books)))
  of less than $(f(min_words)) words in English, totalling $(f(read_short_works[:pages])) pages
  ($(percent(read_short_works, short_works, :pages))), and $(f(read_short_works[:words])) words
  ($(percent(read_short_works, short_works, :words))).

Thus, in total, I have read $(f(total_read[1])) works ($(percent(read_all_works, all_works, :books)))
consisting of $(f(total_read[2])) pages ($(percent(read_all_works, all_works, :pages)))
and $(f(total_read[3])) words ($(percent(read_all_works, all_works, :words))).

"""

for lang in vcat([:all], all_languages)
  foo = """
  $(render_table(lang, :all))
  $(render_table(lang, :long))
  $(render_table(lang, :short))

  """
  if length(foo) > 10
    tmpl *= "## " * language[lang] * foo
  end
end

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


#
# Write the set of all words (whitespace separated strings) from all the books
# I read to a file.
#

### searchdir(path, key) = filter(x -> contains(x, key), readdir(path))
### function full_path_to_txt(rel_path::String)
###   base_path = "/home/joghurt/books/non-fiction/"
###   tmp = searchdir(base_path * rel_path, ".txt")
###   if length(tmp) == 0
###     return false
###   else
###     return base_path * rel_path * "/" * tmp[1]
###   end
### end
###
### function get_paths_of_the_books_i_read_in_language(lang::String)
###   tmp = SQLite.query(db, """SELECT path
### FROM $read
### JOIN books ON($read.book = books.id)
### JOIN books_languages_link ON(books_languages_link.book = books.id)
### JOIN languages ON(languages.id = books_languages_link.lang_code)
### WHERE languages.lang_code = '$lang';""")
###   tmp = map(get, convert(Array, tmp))
###   tmp = filter(x -> x != false, map(full_path_to_txt, tmp))
###   return tmp
### end
###
###
### using TextAnalysis
###
### function sort_lexicon_by_frequency(lexicon::Dict{String,Int64})
###   sort(collect(lexicon), by=x->x[2], rev=true)
### end
###
### write_word_list(lang::String, corpus::Corpus) = write_word_list(lang, corpus, false)
###
### function write_word_list(lang::String, corpus::Corpus, with_multiplicity::Bool)
###   # read=false, write=true, create=true, truncate=true, append=false
###   foo = if with_multiplicity
###     "_mult"
###   else
###     ""
###   end
###   file = open(expanduser("~/prj/library-stats/$(lang)_words$foo.txt"), false, true, true, true, false)
###
###   # Sort the words by descending frequency
###   tmp = sort_lexicon_by_frequency(lexicon(corpus))
###   # and remove unique words (which will usually be typos)
###   filter!(x -> x[2] > 1, tmp)
###
###   if with_multiplicity
###     tmp = map(x -> x[1] * ":" * string(x[2]), tmp)
###   else
###     tmp = map(x -> x[1], tmp)
###   end
###
###   write(file, join(tmp, "\n"))
###   close(file)
### end
###
### corpi = Dict{String,Corpus}()
### for lang in ["deu", "eng"]
###   book_paths = get_paths_of_the_books_i_read_in_language(lang)
###   crps = Corpus(convert(Array{Any}, map(FileDocument, book_paths)))
###
###   # Load the documents into memory
###   standardize!(crps, StringDocument)
###
###   # and remove garbage
###   steps = strip_numbers | strip_case | strip_punctuation | strip_articles
###   prepare!(crps, steps)
###
###   # Analyse the resulting corpus
###   update_lexicon!(crps)
###   corpi[lang] = crps
###   write_word_list(lang, crps)
###   write_word_list(lang, crps, true)
### end
###
### deu_crps = corpi["deu"]
### eng_crps = corpi["eng"]
