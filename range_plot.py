import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pandas.tseries.converter as converter

dropna = True

pd.set_option('display.line_width', 120)
pd.set_option('display.max_columns', 20)

c = converter.DatetimeConverter()

df = pd.read_csv('ranges.csv', parse_dates=['Start', 'End'])
if dropna:
    df.dropna(inplace=True)
else:
    df['Start'].fillna(pd.datetime(1990, 1, 1), inplace=True)
    df['End'].fillna(pd.datetime(2020, 1, 1), inplace=True)
df['Duration'] = df.End - df.Start

num = df.Start.size
error_bars = np.vstack((np.zeros(num, dtype='timedelta64[ns]'), df.Duration.values))
ys = np.array(range(num))

fig = plt.figure()
ax = fig.add_subplot(111)
ax.errorbar(x=df.Start.values, y=ys, xerr=error_bars,
            linestyle='None', elinewidth=2)
plt.show()
