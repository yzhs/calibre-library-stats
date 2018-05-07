from collections import Counter
from datetime import datetime

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd
import pandas.tseries.converter as converter

# Drop all rows missing a start or end date?
dropna = True

# Ignore all entries that start before the following date if != None
cutoff_date = np.datetime64('2012-01-01')

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

# We need to instantiate a DatetimeConverter so we can plot numpy's
# np.datetime64 values.
c = converter.DatetimeConverter()

day = np.timedelta64(1, 'D')


def error_bars(df):
    """Generate a bunch of pairs of the form (0, d) where d is the
    duration. Using this to pass to errorbar(), we get lines starting
    at a data point and going d to the right, i.e. representing the
    time ranges in df."""
    num = df.start.size
    zeros = np.zeros(num, dtype='timedelta64[ns]')
    return np.vstack((zeros, df.duration.values))


def ceil(td, roundto='D'):
    """Round a timedelta to the smallest larger number of days or
    whatever frequency was supplied in the roundto argument."""
    return pd.Timedelta(td).ceil(roundto)


def get_data():
    """Read the data from CSV and do some basic analysis."""
    df = pd.read_csv('ranges.csv', parse_dates=['start', 'end'])

    if dropna:
        df.dropna(inplace=True)
    else:
        df.start.fillna(dummy_start_date, inplace=True)
        df.end.fillna(dummy_end_date, inplace=True)

    durations = (df.end - df.start).map(ceil)
    words_per_day = df.words / (durations / day)
    df = df.assign(duration=durations, words_per_day=words_per_day)

    return df


def allocate_ys(df):
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
    cnt = Counter()

    for date in df.start.values:
        cnt[date] += 1

    for date in df.end.values:
        cnt[date] -= 1

    dates = sorted(cnt.items())
    dates.insert(0, (dummy_start_date, 0))

    return dates


def find_number_of_concurrent_reads(df):
    """Find out how many overlapping events are in the intervals
    between successive event dates, i.e. how many books have been read
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
    dates = {x[0]: 0 for x in dates_sorted(df)}

    for i in range(df.start.size):
        start = df.start.values[i]
        end = df.end.values[i]
        duration = ceil(end - start)
        assert end > start, df.iloc[i]
        words_per_day = df.words.values[i] / (duration / day)
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


def plot_bars(df, fiction, nonfiction, full_date_range=False):
    line_height = 4
    fig = plt.figure(figsize=ranges_plot_size, dpi=dpi)
    ax = fig.add_subplot(311)
    if not full_date_range:
        df = df[df.end >= plot_start_date]
        fiction = df[df.is_fiction]
        nonfiction = df[df.is_fiction == False] # noqa

    ys = allocate_ys(df)

    ax.errorbar(x=fiction.start.values,
                y=ys[df.is_fiction],
                xerr=error_bars(fiction),
                linestyle='None', elinewidth=line_height)

    ax.errorbar(x=nonfiction.start.values,
                y=ys[df.is_fiction == False],  # noqa
                xerr=error_bars(nonfiction),
                linestyle='None', elinewidth=line_height)
    plt.axis([plot_start_date, plot_end_date, -0.5, max(ys)+1])
    plt.xticks([np.datetime64(str(year) + '-01-01T00:00:00.00000000')
                for year in range(1990, 2020)])

    ax2 = fig.add_subplot(312, sharex=ax)

    dates, num_read = find_number_of_concurrent_reads(df)
    ax2.step(dates, num_read)

    dates, num_read = find_number_of_concurrent_reads(nonfiction)
    ax2.step(dates, num_read)

    ax3 = fig.add_subplot(313, sharex=ax)
    dates, num_words = number_of_words(df)
    ax3.step(dates, num_words)
    plt.axis([plot_start_date, plot_end_date, 0, max(num_words)*1.1])

    plt.savefig('bars.png', bbox_inches='tight')


blue_patch = mpatches.Patch(label='Fiction')
orange_patch = mpatches.Patch(label='Nonfiction', color='orange')


def plot_histogram(df, fiction, nonfiction):
    fig = plt.figure(figsize=(8, 6), dpi=dpi)
    ax = fig.add_subplot(111)

    ax.hist([np.array(fiction.duration.map(lambda x: x.days),
                      dtype='float64'),
             np.array(nonfiction.duration.map(lambda x: x.days),
                      dtype='float64')],
            histtype='barstacked',
            bins=list(range(-7, 1764, 14)))

    plt.title('Number of days spent reading a book')
    plt.legend(handles=[blue_patch, orange_patch])

    plt.savefig('histogram.png')


def scatter_length_duration(df, fiction, nonfiction):
    fig = plt.figure(figsize=(8, 6), dpi=dpi)
    ax = fig.add_subplot(111)

    duration = np.array(fiction.duration.map(lambda x: x.days),
                        dtype='float64')
    ax.scatter(fiction.words.values, duration)

    duration = np.array(nonfiction.duration.map(lambda x: x.days),
                        dtype='float64')
    ax.scatter(nonfiction.words.values, duration)

    plt.title("Number of words vs. days of reading")
    plt.xlabel("Number of words")
    plt.ylabel("Days spent reading")
    plt.legend(handles=[blue_patch, orange_patch])

    plt.savefig('scatter.png')


df = get_data()
df.sort_values('start', inplace=True)
fiction = df[df.is_fiction]
nonfiction = df[df.is_fiction == False]  # noqa

plot_bars(df, fiction, nonfiction)
plot_histogram(df, fiction, nonfiction)
scatter_length_duration(df, fiction, nonfiction)
