#[macro_use]
extern crate serde_derive;

extern crate handlebars;
extern crate sqlite;

use std::collections::BTreeMap;
use std::path::PathBuf;

const LIBRARY_PATH: &str = "books/non-fiction";

// TODO read the values from the database?
mod tables {
    #![allow(unused)]

    pub const WORDS: &str = "custom_column_5";
    pub const PAGES: &str = "custom_column_6";

    pub const READ: &str = "custom_column_11";
    pub const STARTED: &str = "custom_column_14";
    pub const FINISHED: &str = "custom_column_13";

    pub const SHELF: &str = "custom_column_15";
    pub const LENT_TO: &str = "custom_column_17";

    pub const FLESCH_KINCAID_GRADE: &str = "custom_column_8";
    pub const GUNNING_FOX_INDEX: &str = "custom_column_9";
    pub const FLESCH_READING_EASE: &str = "custom_column_10";
}

// How many words/pages does a work need to count as a book?
const MIN_WORDS: u32 = 10_000;
const MIN_PAGES: u32 = 100;

#[derive(Debug, Serialize)]
struct Stats {
    works: u32,
    pages: u32,
    words: u64,
}

#[derive(Debug)]
enum Language {
    Eng,
    Deu,
    Jbo,
    Lat,
}

impl<'a> From<&'a str> for Language {
    fn from(name: &'a str) -> Self {
        match name {
            "eng" => Language::Eng,
            "deu" => Language::Deu,
            "jbo" => Language::Jbo,
            "lat" => Language::Lat,
            _ => unimplemented!(),
        }
    }
}

#[derive(Debug)]
enum Read {
    Yes,
    OtherLanguage,
    No,
}

impl From<Option<i64>> for Read {
    fn from(value: Option<i64>) -> Self {
        match value {
            Some(0) => Read::OtherLanguage,
            Some(1) => Read::Yes,
            None => Read::No,
            Some(_) => unimplemented!(),
        }
    }
}

impl Stats {
    fn from_query<S: AsRef<str>>(
        db: &sqlite::Connection,
        condition: S,
    ) -> Vec<(bool, Language, Read, Stats)> {
        // is_short_work = "($words.value < $min_words OR $words.value IS NULL AND $pages.value < $min_pages)"
        // is_long_work = "($words.value >= $min_words OR ($words.value IS NULL AND $pages.value >= $min_pages))"
        let query = format!(
            "SELECT \
                {pages}.value >= {min_pages} OR ifnull({words}.value, 0) >= {min_words} AS is_long, \
                languages.lang_code AS lang, \
                {read}.value AS read, \
                COUNT(*) AS works, \
                SUM({pages}.value) AS pages, \
                SUM(ifnull({words}.value, 0)) AS words \
             FROM books \
             JOIN books_languages_link ON books.id = books_languages_link.book \
             JOIN languages ON languages.id = books_languages_link.lang_code \
             JOIN {pages} ON books.id = {pages}.book \
             LEFT OUTER JOIN {read} ON books.id = {read}.book \
             LEFT OUTER JOIN {words} ON books.id = {words}.book \
             GROUP BY lang, read, is_long \
             {condition}
            ",
            words = tables::WORDS,
            pages = tables::PAGES,
            read = tables::READ,
            min_pages = MIN_PAGES,
            min_words = MIN_WORDS,
            condition = condition.as_ref(),
        );

        let mut cursor = db.prepare(query)
            .expect("Failed to prepare statement")
            .cursor();

        let mut result = vec![];
        while let Some(row) = cursor.next().expect("SQL error") {
            let is_long = row[0].as_integer().unwrap() == 1;
            let lang = Language::from(row[1].as_string().unwrap());
            let read = Read::from(row[2].as_integer());
            let stats = Stats {
                works: row[3].as_integer().unwrap() as u32,
                pages: row[4].as_integer().unwrap() as u32,
                words: row[5].as_integer().unwrap() as u64,
            };
            result.push((is_long, lang, read, stats));
        }
        println!("{:?}", result);
        result
    }
}

fn setup() -> sqlite::Result<sqlite::Connection> {
    let path = PathBuf::from(env!("HOME"))
        .join(LIBRARY_PATH)
        .join("metadata_tmp.db");

    sqlite::open(path)
}

pub fn main() {
    use handlebars::Handlebars;
    let mut handlebars = Handlebars::new();
    let path = PathBuf::new()
        .join(env!("CARGO_MANIFEST_DIR"))
        .join("templates/template.md");
    handlebars
        .register_template_file("markdown", path)
        .expect("Failed to register template");

    let db = setup().expect("Opening database failed");

    let _ = Stats::from_query(&db, "");

    let all = "<all>";
    let long = "<long>";
    let short = "<short>";

    let mut data = BTreeMap::new();
    data.insert("all", all);
    data.insert("long", long);
    data.insert("short", short);

    let md = handlebars
        .render("markdown", &data)
        .expect("Failed to render template");
    println!("{}", md);
}

/*

# Construct a query string and execute the query, returning a dataframe without
# nullable columns
function query(columns   :: Array{Symbol, 1},
               condition :: Union{String, Array{String}},
               group_by  :: Union{String, Array{String}})
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
*/

/*
# Produce a list of all the txt files of books that I have finished.
function toarray(df)
  return convert(Array{String}, map(x -> isnull(x) ? NA : get(x), df))
end
query_string = """SELECT path, title, name FROM $read
LEFT JOIN books ON $read.book = books.id
LEFT JOIN books_authors_link ON books_authors_link.book = books.id
LEFT JOIN authors ON books_authors_link.author = authors.id
;"""

foo = SQLite.query(db, query_string);

library_path = expanduser("~/books/non-fiction/")
file = open(expanduser("~/prj/library-stats/read_books_list.txt"), "w")
write(file, )
for i in 1:size(foo, 1)
  line = foo[i, :]
  dir_path = get(line[:path][1])
  author = normalize_string(get(line[:name][1]), stripmark=true)
  if !contains(dir_path, author)
    continue
  end
  title = get(line[:title][1])
  title = replace(title, "…", "_.")
  title = replace(title, "½", "1_2")
  title = normalize_string(title, stripmark=true)
  path = rstrip(title[1:min(42, length(title))]) * " - " * author * ".txt\n"
  path = replace(path, Set([':' '/' '?']), "_")
  path = library_path * dir_path * "/" * path
  print(path)
  write(file, path)
end
close(file)
*/
