#[macro_use]
extern crate serde_derive;

extern crate handlebars;
extern crate sqlite;

use std::collections::BTreeMap;
use std::ops::Add;
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

impl Add for Stats {
    type Output = Self;
    fn add(self, other: Self) -> Self {
        Stats {
            works: self.works + other.works,
            pages: self.pages + other.pages,
            words: self.words + other.words,
        }
    }
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
    fn query_db<S: AsRef<str>>(db: &sqlite::Connection, condition: S) -> Stats {
        let query = format!(
            "SELECT \
                {pages}.value >= {min_pages} OR
                    ifnull({words}.value, 0) >= {min_words} AS is_long, \
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
             {condition}
            ",
            words = tables::WORDS,
            pages = tables::PAGES,
            read = tables::READ,
            min_pages = MIN_PAGES,
            min_words = MIN_WORDS,
            condition = condition.as_ref()
        );

        let mut cursor = db.prepare(query)
            .expect("Failed to prepare statement")
            .cursor();

        let mut result = Default::default();
        while let Some(row) = cursor.next().expect("SQL error") {
            let stats = Stats {
                works: row[3].as_integer().unwrap() as u32,
                pages: row[4].as_integer().unwrap() as u32,
                words: row[5].as_integer().unwrap() as u64,
            };
            result = result + stats;
        }

        result
    }
}

impl std::default::Default for Stats {
    fn default() -> Self {
        Stats {
            works: 0,
            pages: 0,
            words: 0,
        }
    }
}

fn db_setup() -> sqlite::Result<sqlite::Connection> {
    let path = PathBuf::from(env!("HOME"))
        .join(LIBRARY_PATH)
        .join("metadata_tmp.db");

    sqlite::open(path)
}

#[derive(Serialize)]
struct TemplateParameter {
    min_pages: u32,
    min_words: u32,
    stats: BTreeMap<&'static str, Stats>,
}

fn read_stats_from_db() -> BTreeMap<&'static str, Stats> {
    let db = db_setup().expect("Opening database failed");

    let all = Stats::query_db(&db, "");
    let read = Stats::query_db(&db, "WHERE read = 1");
    let read_eng = Stats::query_db(&db, "WHERE lang = 'Eng' AND read = 1");
    let read_deu = Stats::query_db(&db, "WHERE lang = 'Deu' AND read = 1");

    let read_long = Stats::query_db(&db, "WHERE is_long AND read = 1");
    let eng_read_long = Stats::query_db(&db, "WHERE lang = 'Eng' AND is_long AND read = 1");
    let deu_read_long = Stats::query_db(&db, "WHERE lang = 'Deu' AND is_long AND read = 1");

    let read_short = Stats::query_db(&db, "WHERE NOT is_long AND read = 1");
    let eng_read_short = Stats::query_db(&db, "WHERE lang = 'Eng' AND NOT is_long AND read = 1");
    let deu_read_short = Stats::query_db(&db, "WHERE lang = 'Deu' AND NOT is_long AND read = 1");

    let mut stats: BTreeMap<_, Stats> = BTreeMap::new();
    stats.insert("all", all);
    stats.insert("read", read);
    stats.insert("read_eng", read_eng);
    stats.insert("read_deu", read_deu);

    stats.insert("read_long", read_long);
    stats.insert("eng_read_long", eng_read_long);
    stats.insert("deu_read_long", deu_read_long);

    stats.insert("read_short", read_short);
    stats.insert("eng_read_short", eng_read_short);
    stats.insert("deu_read_short", deu_read_short);

    stats
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

    let param = TemplateParameter {
        min_pages: MIN_PAGES,
        min_words: MIN_WORDS,
        stats: read_stats_from_db(),
    };

    let md = handlebars
        .render("markdown", &param)
        .expect("Failed to render template");
    println!("{}", md);
}

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
