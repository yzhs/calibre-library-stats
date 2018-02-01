extern crate atomicwrites;
extern crate chrono;
extern crate handlebars;
#[macro_use]
extern crate serde_derive;
extern crate sqlite;

use std::collections::BTreeMap;
use std::ops::Add;
use std::path::{Path, PathBuf};

use chrono::{Local, Timelike};
use handlebars::{Handlebars, Helper, JsonRender, RenderContext, RenderError};

const LIBRARY_PATH: &str = "books/non-fiction";
const OUTPUT_PATH: &str = "site/local/content/library.md";

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
            include_str!("query.sql"),
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
    now: String,
    stats: BTreeMap<&'static str, Stats>,
}

fn collect_stats_from_db() -> BTreeMap<&'static str, Stats> {
    let db = db_setup().expect("Opening database failed");

    let all = Stats::query_db(&db, "");
    let read = Stats::query_db(&db, "WHERE read = 1");
    let read_eng = Stats::query_db(&db, "WHERE lang = 'eng' AND read = 1");
    let read_deu = Stats::query_db(&db, "WHERE lang = 'deu' AND read = 1");

    let read_long = Stats::query_db(&db, "WHERE is_long AND read = 1");
    let eng_read_long = Stats::query_db(&db, "WHERE lang = 'eng' AND is_long AND read = 1");
    let deu_read_long = Stats::query_db(&db, "WHERE lang = 'deu' AND is_long AND read = 1");

    let read_short = Stats::query_db(&db, "WHERE NOT is_long AND read = 1");
    let eng_read_short = Stats::query_db(&db, "WHERE lang = 'eng' AND NOT is_long AND read = 1");
    let deu_read_short = Stats::query_db(&db, "WHERE lang = 'deu' AND NOT is_long AND read = 1");

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

type HelperResult = Result<(), RenderError>;

fn group_digits_helper(h: &Helper, _: &Handlebars, rc: &mut RenderContext) -> HelperResult {
    let param = h.param(0).unwrap();

    let digits = param.value().render();

    let len = digits.len();
    let result = if len <= 4 {
        digits.into()
    } else {
        let mut tmp = "".to_owned();
        let mut i = len;
        for d in digits.chars() {
            if i % 3 == 0 && i != len {
                tmp.push('\u{202F}'); // Narrow no-break space
            }
            tmp.push(d);
            i -= 1;
        }
        tmp
    };

    try!(rc.writer.write(result.into_bytes().as_ref()));
    Ok(())
}

fn generate_markdown(template_param: &TemplateParameter) -> String {
    //use std::boxed::Box;
    let mut handlebars = Handlebars::new();
    let path = PathBuf::new()
        .join(env!("CARGO_MANIFEST_DIR"))
        .join("templates/template.md");

    handlebars
        .register_template_file("markdown", path)
        .expect("Failed to register template");

    handlebars.register_helper("group-digits", Box::new(group_digits_helper));

    handlebars
        .render("markdown", template_param)
        .expect("Failed to render template")
}

fn save_markdown<P: AsRef<Path>>(path: P, content: &str) {
    use std::io::Write;

    let af = atomicwrites::AtomicFile::new(path, atomicwrites::AllowOverwrite);
    af.write(|f| f.write_all(content.as_bytes()))
        .expect("Failed to write output file");
}

pub fn main() {
    let param = TemplateParameter {
        now: Local::now().with_nanosecond(0).unwrap().to_rfc3339(),
        min_pages: MIN_PAGES,
        min_words: MIN_WORDS,
        stats: collect_stats_from_db(),
    };

    let md = generate_markdown(&param);
    let path = PathBuf::from(env!("HOME")).join(OUTPUT_PATH);
    save_markdown(path, &md);

    println!("{}", md);
}
