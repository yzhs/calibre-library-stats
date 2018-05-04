from collections import Counter

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd
import pandas.tseries.converter as converter

dropna = False
dpi = 130
bars_size = (32, 8)

dummy_start_date = pd.datetime(1990, 1, 1)
dummy_end_date = pd.datetime(2020, 1, 1)

pd.set_option('display.line_width', 120)
pd.set_option('display.max_columns', 20)

c = converter.DatetimeConverter()


def error_bars(df):
    num = df.Start.size
    zeros = np.zeros(num, dtype='timedelta64[ns]')
    return np.vstack((zeros, df.Duration.values))


def ceil(td, roundto='D'):
    return pd.Timedelta(td).ceil(roundto)


def get_data():
    df = pd.read_csv('ranges.csv', parse_dates=['Start', 'End'])

    if dropna:
        df.dropna(inplace=True)
    else:
        df['Start'].fillna(dummy_start_date, inplace=True)
        df['End'].fillna(dummy_end_date, inplace=True)

    df['Duration'] = (df.End - df.Start).map(ceil)

    return df


def allocate_ys(df):
    n = df.Start.size
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
                if df.End.values[registers[j]] < df.Start.values[i]:
                    registers[j] = i
                    result.append(j)
                    break

    return np.array(result)


def find_number_of_concurrent_reads(df):
    """Find out how many overlapping events are in the intervals
    between successive event dates, i.e. how many books have been read
    concurrently in that time frame.
    """
    cnt = Counter()
    for date in df.Start.values:
        cnt[date] += 1
    for date in df.End.values:
        cnt[date] -= 1
    dates = sorted(cnt.items())
    dates.insert(0, (dummy_start_date, 0))

    num_read = []
    counter = 0
    for date, difference in dates:
        counter += difference
        num_read.append(counter)

    return [x[0] for x in dates][:-1], num_read[:-1]


def plot_bars(df, fiction, nonfiction, full_date_range=False):
    line_height = 4
    fig = plt.figure(figsize=bars_size, dpi=dpi)
    ax = fig.add_subplot(211)
    if not full_date_range:
        df = df[df['End'] >= pd.datetime(2007, 1, 1)]
        fiction = df[df['IsFiction']]
        nonfiction = df[df['IsFiction'] == False] # noqa

    ys = allocate_ys(df)

    ax.errorbar(x=fiction.Start.values,
                y=ys[df['IsFiction']],
                xerr=error_bars(fiction),
                linestyle='None', elinewidth=line_height)

    ax.errorbar(x=nonfiction.Start.values,
                y=ys[df['IsFiction'] == False],  # noqa
                xerr=error_bars(nonfiction),
                linestyle='None', elinewidth=line_height)

    ax2 = fig.add_subplot(212, sharex=ax)

    dates, num_read = find_number_of_concurrent_reads(df)
    ax2.step(dates, num_read)

    dates, num_read = find_number_of_concurrent_reads(nonfiction)
    ax2.step(dates, num_read)

    plt.savefig('bars.png', bbox_inches='tight')


def plot_histogram(df, fiction, nonfiction):
    fig = plt.figure(figsize=(8, 6), dpi=dpi)
    ax = fig.add_subplot(111)

    ax.hist([np.array(fiction['Duration'].map(lambda x: x.days),
                      dtype='float64'),
             np.array(nonfiction['Duration'].map(lambda x: x.days),
                      dtype='float64')],
            histtype='barstacked',
            bins=list(range(-7, 1764, 14)))

    plt.title('Number of days spent reading a book')
    blue_patch = mpatches.Patch(label='Fiction titles')
    orange_patch = mpatches.Patch(color='orange',
                                  label='Nonfiction titles')
    plt.legend(handles=[blue_patch, orange_patch])

    plt.savefig('histogram.png')


df = get_data()
df.sort_values('Start', inplace=True)
fiction = df[df['IsFiction']]
nonfiction = df[df['IsFiction'] == False]  # noqa

plot_bars(df, fiction, nonfiction)
plot_histogram(df, fiction, nonfiction)
