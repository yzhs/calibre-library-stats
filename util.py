from collections import Counter
from datetime import datetime
from os.path import expanduser

import altair as alt
import numpy as np
import pandas as pd
from scipy.stats.stats import pearsonr
import sqlite3

from config import output_dir


def ceil(td, roundto='D'):
    """Round a timedelta to the smallest larger number of days or
    whatever frequency was supplied in the roundto argument."""
    return pd.Timedelta(td).ceil(roundto)


def to_year(x):
    "Given a date, return the year, otherwise return NA"
    if pd.isna(x):
        return x
    return int(x.year)


def to_month(x):
    "Given a date, return the month, otherwise return NA"
    if pd.isna(x):
        return x
    return int(x.month)


def to_day(x):
    "Given a date, return the day, otherwise return NA"
    if pd.isna(x):
        return x
    return int(x.day)


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


def save_plot(plot, output_file):
    plot.save(output_dir + output_file)
