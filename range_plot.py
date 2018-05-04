import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd
import pandas.tseries.converter as converter

dropna = True
savefig_dpi = 130

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
        df['Start'].fillna(pd.datetime(1990, 1, 1), inplace=True)
        df['End'].fillna(pd.datetime(2020, 1, 1), inplace=True)

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


def plot_bars(df, fiction, nonfiction):
    line_height = 4
    fig = plt.figure()
    ax = fig.add_subplot(111)

    ys = allocate_ys(df)

    ax.errorbar(x=fiction.Start.values,
                y=ys[df['IsFiction']],
                xerr=error_bars(fiction),
                linestyle='None', elinewidth=line_height)

    ax.errorbar(x=nonfiction.Start.values,
                y=ys[df['IsFiction'] == False],
                xerr=error_bars(nonfiction),
                linestyle='None', elinewidth=line_height)

    plt.savefig('bars.png', dpi=savefig_dpi)


def plot_histogram(df, fiction, nonfiction):
    fig = plt.figure()
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

    plt.savefig('histogram.png', dpi=savefig_dpi)


df = get_data()
df.sort_values('Start', inplace=True)
fiction = df[df['IsFiction']]
nonfiction = df[df['IsFiction'] == False]

plot_bars(df, fiction, nonfiction)
plot_histogram(df, fiction, nonfiction)
