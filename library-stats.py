import os
from os.path import expanduser

import altair as alt
import numpy as np
import pandas as pd
from scipy.stats.stats import pearsonr
import sqlite3

from util import to_day, to_month, to_year, to_local, allocate_ys, save_plot
from config import dummy_start_date, dummy_end_date, cutoff_date

# %matplotlib inline


plot_start_date = dummy_start_date
plot_end_date = dummy_end_date
if cutoff_date is not None:
    plot_start_date = cutoff_date

day = np.timedelta64(1, 'D')
fiction_scale = alt.Scale(domain=[True, False])


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


def plot_ranges(df, output='ranges.html'):
    """Print date ranges in which the books have been is_read, how many
    books have been is_read at any given point in time and how many words
    have been is_read per day.
    """
    if cutoff_date is not None:
        # df = df[(df.start >= cutoff_date) & (df.end >= cutoff_date)]
        df = df[df.end.isna() | (df.end >= cutoff_date)]
    df.end.fillna(dummy_end_date)
    df = df[df.start.notna()].assign(ys=-allocate_ys(df[df.start.notna()]))

    bars = alt.Chart(df) \
        .mark_bar(clip=True) \
        .encode(
            x=alt.X('start', axis=alt.Axis(labelAngle=45, title='Date')),
            x2='end',
            y=alt.Y('ys:N', axis=None),
            color=alt.Color('is_fiction', scale=fiction_scale, legend=None),
            tooltip='title'
        )
    bars.width = 1600

    overlapped = alt.Chart(df[df.start.notna()]) \
        .mark_bar(clip=True, opacity=0.1) \
        .encode(
            x=alt.X('start', axis=None),
            x2='end',
            y=alt.Y('is_fiction', axis=None),
            color=alt.Color('is_fiction', scale=fiction_scale, legend=None)
        )
    overlapped.width = bars.width

    baz = df[df.series.notna()]
    if cutoff_date is not None:
        baz = baz[baz.start.notna() & (baz.end.isna() |
                                       (baz.end >= cutoff_date))]
    else:
        baz = baz[df.start.notna()]
    by_series = alt.Chart(baz) \
        .mark_bar(clip=True, opacity=0.7) \
        .encode(
            x=alt.X('start', axis=alt.Axis(labelAngle=45, title='Date')),
            x2='end',
            y=alt.Y('series', title='Series'),
            tooltip='title'
        )
    by_series.width = bars.width

    baz = df[df.author.notna()]
    if cutoff_date is not None:
        baz = baz[baz.start.notna() & (baz.end.isna() |
                                       (baz.end >= cutoff_date))]
    else:
        baz = baz[df.start.notna()]
    baz.ys = -allocate_ys(baz[baz.start.notna()])
    by_author = alt.Chart(baz) \
        .mark_bar(clip=True, opacity=0.7) \
        .encode(
            x=alt.X('start', axis=alt.Axis(labelAngle=45, title='Date')),
            x2='end',
            y=alt.Y('author', title='Author'),
            color='series',
            tooltip='title'
        )
    by_author.width = bars.width

    save_plot(overlapped & bars & by_series, output)
    save_plot(by_author, 'by_author.html')


def plot_yearly(df, y='count()', output='finished.html'):
    chart = alt.Chart(df[df.is_read & df.end]) \
        .mark_bar() \
        .encode(
            x='finished_year:O',
            y=y,
            color=alt.Color('is_fiction', scale=fiction_scale),
        )
    save_plot(chart, output)


def number_of_books_per_author(df, output='books_per_author.html'):
    df = df[df.is_read]
    x = df.author.value_counts()
    foo = pd.DataFrame(data={'author': x.index,
                             'count': x.values})
    foo.sort_values('count', ascending=False, inplace=True)

    chart = alt.Chart(foo) \
        .mark_bar() \
        .encode(y=alt.Y('author', sort=None), x='count')
    save_plot(chart, output)


def plot_pubdate(df, output='pubdate.html'):
    df = df[df.pubdate.notna()]

    years = alt.Chart(df).mark_bar().encode(x='pubyear:O', y='count(year):N')
    years_nonfiction = alt.Chart(df[~df.is_fiction]) \
        .mark_bar(color='orange') \
        .encode(x='pubyear:O', y='count(year):N')
    months = alt.Chart(df).mark_bar().encode(x='pubmonth:O',
                                             y='count(pubmonth):N')
    days = alt.Chart(df).mark_bar().encode(x='pubday:O', y='count(pubday):N')
    years.width = 965
    save_plot((years + years_nonfiction) & (months | days), output)


def reading_ease(df):
    df = df[df.fre.notna() & df.fkg.notna() & df.gfi.notna()]
    opacity = 0.2
    color = alt.Color('is_fiction', scale=fiction_scale)

    a = alt.Chart(df).mark_point(opacity=opacity) \
        .encode(x='fre', y='fkg', color=color)
    b = alt.Chart(df).mark_point(opacity=opacity) \
        .encode(x='fre', y='gfi', color=color)

    save_plot(a | b, 'reading_ease.html')


# blue_patch = mpatches.Patch(label='Fiction')
# orange_patch = mpatches.Patch(label='Nonfiction', color='orange')
#
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


os.makedirs('output', exist_ok=True)

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
