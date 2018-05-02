import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pandas.tseries.converter as converter

dropna = True

pd.set_option('display.line_width', 120)
pd.set_option('display.max_columns', 20)

c = converter.DatetimeConverter()


def error_bars(df):
    num = df.Start.size
    zeros = np.zeros(num, dtype='timedelta64[ns]')
    return np.vstack((zeros, df.Duration.values))


def ceil(td):
    return pd.Timedelta(td).ceil('D')


def get_data():
    df = pd.read_csv('ranges.csv', parse_dates=['Start', 'End'])

    if dropna:
        df.dropna(inplace=True)
    else:
        df['Start'].fillna(pd.datetime(1990, 1, 1), inplace=True)
        df['End'].fillna(pd.datetime(2020, 1, 1), inplace=True)

    df['Duration'] = (df.End - df.Start).map(ceil)

    return df


df = get_data()
fiction = df[df['IsFiction']]
nonfiction = df[df['IsFiction'] == False]

fig = plt.figure()
ax = fig.add_subplot(111)
ys = np.array(range(fiction.Start.size))
ax.errorbar(x=fiction.Start.values, y=ys, xerr=error_bars(fiction),
            linestyle='None', elinewidth=2)
ys = np.array(range(nonfiction.Start.size))
ax.errorbar(x=nonfiction.Start.values, y=ys, xerr=error_bars(nonfiction),
            linestyle='None', elinewidth=2)
plt.show()
