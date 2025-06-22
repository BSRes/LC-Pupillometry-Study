
# --- BLINKS AND SACCADES --- #
BLINK_PRE_PADDING = 10
BLINK_POST_PADDING = 50

SACCADE_PRE_PADDING = 10
SACCADE_POST_PADDING = 20

# --- INTERPOLATION ALLOWANCE --- #
INTERPOLATION_PC_THRESHOLD = 50.0 # Max percent of a trail that can be interpolated data - above this gets rejected.


# --- EPOCH SETTINGS --- #
EPOCH_START = 1000 # ms from main-stimulus onset.
EPOCH_END = 1600 # ms from main-stimulus onset.

# --- BEHAVIOURAL RESPONSES --- #
BEHAVIOURAL_BUFFER = EPOCH_END # ms from main-stimulus onset - if a target was shown before this, the trial is rejected.