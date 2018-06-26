from os.path import expanduser

from datetime import datetime
import numpy as np


# Directory in which the library stats code lives
base_dir = expanduser('~/prj/library-stats/')
output_dir = base_dir + 'output/'

# Drop all rows missing a start or end date?
dropna = True

# Ignore all entries that start before the following date if != None
#cutoff_date = None
#cutoff_date = np.datetime64('2008-01-01')
#cutoff_date = np.datetime64('2012-08-01')
cutoff_date = np.datetime64('2015-01-01')

# DPI for the generated image files
dpi = 130

# How large is the ranges plot (in inches)?
ranges_plot_size = (32, 9)

# If we do not drop NAs, use these dummy dates to fill in the start and
# end columns, respectively.
dummy_start_date = np.datetime64('1990-01-01T00:00:00.00000000')
dummy_end_date = np.datetime64(datetime.now())
