from collections import Counter
from datetime import datetime
from os.path import expanduser

import altair as alt
import numpy as np
import pandas as pd
from scipy.stats.stats import pearsonr
import sqlite3

# %matplotlib inline
# Directory in which the library stats code lives
base_dir = expanduser('~/prj/library-stats/')
output_dir = base_dir + 'output/'

# Drop all rows missing a start or end date?
dropna = True

# Ignore all entries that start before the following date if != None
cutoff_date = None
# cutoff_date = np.datetime64('2012-08-01')

# DPI for the generated image files
dpi = 130

# How large is the ranges plot (in inches)?
ranges_plot_size = (32, 9)

# If we do not drop NAs, use these dummy dates to fill in the start and
# end columns, respectively.
dummy_start_date = np.datetime64('1990-01-01T00:00:00.00000000')
dummy_end_date = np.datetime64(datetime.now())


plot_start_date = dummy_start_date
plot_end_date = dummy_end_date
if cutoff_date is not None:
    plot_start_date = cutoff_date

day = np.timedelta64(1, 'D')


def ceil(td, roundto='D'):
    """Round a timedelta to the smallest larger number of days or
    whatever frequency was supplied in the roundto argument."""
    return pd.Timedelta(td).ceil(roundto)


def get_data(library_paths=[expanduser('~/books/non-fiction/')]):
    db_path = library_paths[0] + 'metadata.db'
    conn = sqlite3.connect(db_path)

    custom_column_index = dict(pd.read_sql_query("""
        SELECT label, id FROM custom_columns
    """, conn).to_dict(orient='split')['data'])

    def tbl(name):
        return 'custom_column_' + str(custom_column_index[name])

    df = pd.read_sql_query(f"""
        SELECT
            title,
            author_sort AS author,
            series.name AS series,
            series_index,
            pubdate,
            timestamp,
            last_modified,
            languages.lang_code AS language,
            {tbl('started')}.value AS start,
            {tbl('finished')}.value AS end,
            {tbl('words')}.value AS words,
            {tbl('pages')}.value AS pages,
            {tbl('fre')}.value AS fre,
            {tbl('fkg')}.value AS fkg,
            {tbl('gfi')}.value AS gfi,
            ({tbl('shelf')}.value = 'Fiction') AS is_fiction,
            ifnull({tbl('read')}.value, 0) AS is_read
        FROM books
        LEFT OUTER JOIN books_series_link
            ON books.id = books_series_link.book
        LEFT OUTER JOIN series
            ON books_series_link.series = series.id
        JOIN books_languages_link
            ON books.id = books_languages_link.book
        JOIN languages
            ON books_languages_link.lang_code = languages.id
        LEFT OUTER JOIN {tbl('pages')}
            ON {tbl('pages')}.book = books.id
        LEFT OUTER JOIN {tbl('words')}
            ON {tbl('words')}.book = books.id
        LEFT OUTER JOIN {tbl('fre')}
            ON {tbl('fre')}.book = books.id
        LEFT OUTER JOIN {tbl('fkg')}
            ON {tbl('fkg')}.book = books.id
        LEFT OUTER JOIN {tbl('gfi')}
            ON {tbl('gfi')}.book = books.id
        JOIN books_{tbl('shelf')}_link
            ON books_{tbl('shelf')}_link.book = books.id
        JOIN {tbl('shelf')}
            ON {tbl('shelf')}.id = books_{tbl('shelf')}_link.value
        LEFT OUTER JOIN {tbl('started')}
            ON {tbl('started')}.book = books.id
        LEFT OUTER JOIN {tbl('finished')}
            ON {tbl('finished')}.book = books.id
        LEFT OUTER JOIN {tbl('read')} ON {tbl('read')}.book = books.id
        WHERE
            {tbl('shelf')}.value = 'Fiction'
            OR {tbl('shelf')}.value = 'Nonfiction'
        """, conn, parse_dates=['start', 'end', 'pubdate', 'timestamp',
                                'last_modified'])

    # Books with no page count are either simply placeholders, not a
    # proper part of the library, or have just been added. In both
    # cases, it is OK to ignore them.
    df = df.loc[df.pages.notna()]

    # Fix data types
    df.language = df.language.astype('category')
    df.pages = df.pages.astype('int64')
    # We cannot make df.words an int64 column, as some PDF files have
    # no word count associated with them and int64 columns cannot
    # contain NAs.
    df.is_fiction = df.is_fiction.astype(bool)
    df.is_read = df.is_read.astype(bool)

    # Compute intermediate columns
    df.pubdate = df.pubdate.map(to_local)
    df = df.assign(words_per_page=df.words / df.pages,
                   words_per_day=df.words / ((df.end - df.start) / day))

    def to_numeric(x):
        return pd.to_numeric(x, errors='coerce', downcast='integer')
    df = df.assign(finished_year=to_numeric(df.end.map(to_year)),
                   finished_month=to_numeric(df.end.map(to_month)),
                   finished_day=to_numeric(df.end.map(to_day)))
    df = df.assign(pubyear=to_numeric(df.pubdate.map(to_year)),
                   pubmonth=to_numeric(df.pubdate.map(to_month)),
                   pubday=to_numeric(df.pubdate.map(to_day)))

    df.sort_values('start', inplace=True)

    return df


def to_local(x):
    """Convert date to the correct local time"""
    if pd.isna(x):
        return x
    return x + pd.Timedelta('02:00:00')


def allocate_ys(df):
    """
    Associate (a small number of) non-negative integers with each
    book containing a start and end date in such a way that any two
    books that have been is_read at the same time have different numbers.

    This is similar to a register allocation problem: Each number
    corresponds to a register, i.e. there is a potentially infinite
    number of registers, and each book has a lifetime during which it
    is to be held in a register. No two books can share a register, but
    registers can be reused after the previous book in the register has
    been finished.
    """
    n = df.start.size
    result = []

    max_register = 0
    registers = {}

    # Greedily allocate registers
    for i in range(n):
        for j in range(max_register+1):
            if j not in registers:
                registers[j] = i
                result.append(j)
                if j == max_register:
                    max_register += 1
                break
            else:
                if df.end.values[registers[j]] < df.start.values[i]:
                    registers[j] = i
                    result.append(j)
                    break

    return np.array(result)


def dates_sorted(df):
    """
    Return a sorted list of dates at which the number of concurrently
    is_read books change, and together with  how much they change at that
    time.  If, for example, exactly one book was finished at some date,
    the entry for that date is -1.

    If the dates have not been rounded, it is likely that the changes
    represented in this list will have distinct dates, so each change
    is either +1 or -1. If, however, we round the dates, say the the
    closest Monday, the change could easily have a much larger absolute
    value.
    """
    cnt = Counter()
    df = df.sort_values('start')

    for date in df.start.dropna():
        cnt[date] += 1

    for date in df.end.dropna():
        cnt[date] -= 1

    dates = sorted(cnt.items())
    dates.insert(0, (dummy_start_date, 0))

    return dates


def find_number_of_concurrent_reads(df):
    """Find out how many overlapping events are in the intervals
    between successive event dates, i.e. how many books have been is_read
    concurrently in that time frame.
    """
    dates = dates_sorted(df)

    num_read = []
    counter = 0

    for date, difference in dates:
        num_read.append(counter)
        counter += difference

    return [x[0] for x in dates], num_read


def number_of_words(df):
    """Estimate how many words have been is_read on which day."""
    dates = {x[0]: 0 for x in dates_sorted(df)}

    df = df[df.start.notna() & df.end.notna()]

    for i in df.start.index:
        start = df.start.loc[i]
        end = df.end.loc[i]
        duration = ceil(end - start)
        assert end > start, df.iloc[i]
        words_per_day = df.words.loc[i] / (duration / day)
        dates[start] += words_per_day
        dates[end] -= words_per_day

    prev_date = dummy_start_date
    num_words = [0]
    counter = 0

    for date, difference in sorted(dates.items()):
        counter += difference
        if date == prev_date:
            continue
        num_words.append(counter)
        prev_date = date

    return sorted(dates.keys())[:-1], num_words[:-1]


fiction_scale = alt.Scale(domain=[True, False])


def plot_ranges(df, output='ranges.html'):
    """Print date ranges in which the books have been is_read, how many
    books have been is_read at any given point in time and how many words
    have been is_read per day.
    """
    if cutoff_date is not None:
        foo = df[(df.start >= cutoff_date) & (df.end >= cutoff_date)]
    else:
        foo = df
    foo = foo[foo.is_read].assign(ys=-allocate_ys(foo[foo.is_read]))

    dates = pd.date_range(start=dummy_start_date,
                          end=dummy_end_date,
                          freq='3M').astype(int) / 10**6 + 86400000

    chart = alt.Chart(foo) \
        .mark_bar(clip=True) \
        .encode(
            x=alt.X('start', axis=alt.Axis(values=list(dates), labelAngle=45)),
            x2='end',
            y=alt.Y('ys:N', axis=None),
            color=alt.Color('is_fiction', scale=fiction_scale),
            tooltip='title'
        )

    chart.width = 1600
    chart.save(output_dir + output)


# blue_patch = mpatches.Patch(label='Fiction')
# orange_patch = mpatches.Patch(label='Nonfiction', color='orange')


# def plot_bars(df, full_date_range=False):
#     if not full_date_range:
#         df = df[df.end >= plot_start_date]
#
#     nonfiction = df[~df.is_fiction]
#
#     # Number of concurrent reads
#     dates, num_read = find_number_of_concurrent_reads(df)
#     ax2.step(dates, num_read)
#
#     dates, num_read = find_number_of_concurrent_reads(nonfiction)
#     ax2.step(dates, num_read)
#     plt.ylabel("Books is_read concurrently")
#
#     # Mean words per day
#     ax3 = fig.add_subplot(313, sharex=ax2)
#     dates, num_words = number_of_words(df)
#     ax3.step(dates, num_words)
#     plt.axis([plot_start_date, plot_end_date, 0, max(num_words)*1.1])
#     plt.ylabel("Words per day")
#
#     plt.savefig('bars.png', bbox_inches='tight')
#     return plt.show()


# def plot_histogram(df):
#     "Plot histogram of how many days I needed to is_read a book."
#     fig = plt.figure(figsize=(8, 6), dpi=dpi)
#     ax = fig.add_subplot(111)
#
#     ax.hist([np.array(df[df.is_fiction].duration
#                       .map(lambda x: x.days).dropna(),
#                       dtype='float64'),
#              np.array(df[~df.is_fiction].duration
#                       .map(lambda x: x.days).dropna(),
#                       dtype='float64')],
#             histtype='barstacked',
#             bins=list(range(-7, 1764, 14)))
#
#     plt.title('Number of days spent reading a book')
#     plt.legend(handles=[blue_patch, orange_patch])
#     plt.xlabel("Number of days spent reading")
#     plt.ylabel("Number of books")
#
#     plt.savefig('histogram.png')
#     return plt.show()
#
#
# def scatter_length_duration(df):
#     fig = plt.figure(figsize=(8, 6), dpi=dpi)
#     ax = fig.add_subplot(111)
#     df = df[df.words > 0]
#     fiction = df[df.is_fiction]
#     nonfiction = df[~df.is_fiction]
#
#     duration = np.array(fiction.duration.map(lambda x: x.days),
#                         dtype='float64')
#     ax.scatter(fiction.words.values, duration)
#
#     duration = np.array(nonfiction.duration.map(lambda x: x.days),
#                         dtype='float64')
#     ax.scatter(nonfiction.words.values, duration)
#
#     plt.title("Number of words vs. days of reading")
#     plt.xlabel("Number of words")
#     plt.ylabel("Days spent reading")
#     plt.legend(handles=[blue_patch, orange_patch])
#
#     plt.savefig('scatter.png')
#     return plt.show()
#
#
# def scatter_words_vs_words_per_day(df):
#     fig = plt.figure()
#     ax = fig.gca()
#     ax.set_xscale('log')
#     ax.set_yscale('log')
#     ax.set_xlabel('Words')
#     ax.set_ylabel('Words per day')
#     ax.plot(df.words, df.words_per_day, 'o')


def to_year(x):
    if pd.isna(x):
        return x
    return int(x.year)


def to_month(x):
    if pd.isna(x):
        return x
    return int(x.month)


def to_day(x):
    if pd.isna(x):
        return x
    return int(x.day)


def plot_yearly(df, y='count()', output='finished.html'):
    chart = alt.Chart(df[df.is_read & df.end]) \
        .mark_bar() \
        .encode(
            x='finished_year:O',
            y=y,
            color=alt.Color('is_fiction', scale=fiction_scale),
        )
    chart.save(output_dir + output)


def number_of_books_per_author(df, output='books_per_author.html'):
    df = df[df.is_read]
    x = df.author.value_counts()
    foo = pd.DataFrame(data={'author': x.index,
                             'count': x.values})
    foo.sort_values('count', ascending=False, inplace=True)

    chart = alt.Chart(foo) \
        .mark_bar() \
        .encode(y=alt.Y('author', sort=None), x='count')
    chart.save(output_dir + output)


def plot_pubdate(df, output='pubdate.html'):
    df = df[df.pubdate.notna()]

    years = alt.Chart(df).mark_bar().encode(x='pubyear', y='count(year):N')
    years_nonfiction = alt.Chart(df[~df.is_fiction]) \
        .mark_bar(color='orange') \
        .encode(x='pubyear', y='count(year):N')
    months = alt.Chart(df).mark_bar().encode(x='pubmonth:O',
                                             y='count(pubmonth):N')
    days = alt.Chart(df).mark_bar().encode(x='pubday:O', y='count(pubday):N')
    years.width = 1000
    ((years + years_nonfiction) & (months | days)).save(output_dir + output)


def reading_ease(df):
    output = 'reading_ease.html'
    opacity = 0.2
    df = df[df.fre.notna() & df.fkg.notna() & df.gfi.notna()]
    color = alt.Color('is_fiction', scale=fiction_scale)
    a = alt.Chart(df).mark_point(opacity=opacity) \
        .encode(x='fre', y='fkg', color=color)
    b = alt.Chart(df).mark_point(opacity=opacity) \
        .encode(x='fre', y='gfi', color=color)
    (a | b).save(output_dir + output)


df = get_data()
avg_words_per_page = df.words.sum() / df.pages[df.words.notna()].sum()

plot_ranges(df)
number_of_books_per_author(df)

plot_yearly(df, output='books_finished.html')
plot_yearly(df, y='sum(pages)', output='pages_finished.html')
plot_yearly(df, y='sum(words)', output='words_finished.html')

plot_pubdate(df)

values = ('words', 'pages')
table = df.pivot_table(values=values,
                       index=('is_read', 'is_fiction', 'language'),
                       aggfunc=np.sum).reset_index()
table = table.assign(combined=list(zip(table.is_fiction, table.is_read)))

chart = alt.Chart(table) \
    .mark_bar() \
    .encode(column='language',
            x='is_read',
            y='words',
            color='language')

ease_df = df[df.fre.notna() & df.fkg.notna() & df.gfi.notna()]
cor_fre_fkg = pearsonr(ease_df.fre, ease_df.fkg)
cor_fre_gfi = pearsonr(ease_df.fre, ease_df.gfi)
cor_fkg_gfi = pearsonr(ease_df.fkg, ease_df.gfi)

reading_ease(df)
