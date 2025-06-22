import logging

# --- Basic display settings (adjust to match the current monitor and setup) ---
FPS = 99.93 # 99.930 # Higher frame-rates effectively "slow" the experiment down to compensate
SCREEN_WIDTH_PX = 1920
SCREEN_HEIGHT_PX = 1080
SCREEN_WIDTH_CM = 60
VIEW_DIST_CM = 72


# --- EyeLink Settings ---
# Set DUMMY_MODE to True to test without a tracker connection
DUMMY_MODE = False
# Calibration target size
CALIBRATION_TARGET_SIZE = 24 # In pixels


# --- Test Trial Settings ---
TRIAL_DURATION_SEC = 10.0 # How long to show the fixation cross


# --- Paths ---
# Create a folder named 'results_test' in the same directory as the script
RESULTS_FOLDER = 'data'
IMAGES_FOLDER = 'images' # grab these from the SR research psychopy examples at the EyeLink install location.
STIMULI_FOLDER = 'stimuli_images'


# --- Study Settings ---
STUDY_NAME = "lc_pupil_size_study"


# --- Stimuli Settings ---
BG_COLOUR = [0, 0, 0]

FINE_GABOR_FILENAME = "fine_gabor"
COARSE_GABOR_FILENAME = "coarse_gabor"
NOISE_DISK_FILENAME = "noise_disk"

# Define colours to be used for the attention stimuli, both normally and when colour is used to prompt a response:
STANDARD_COLOUR = (-.5, -.5, -.5)
RESPONSE_COLOUR = (0, 0, 1)

# Define settings for messages, such as instruction text:
MESSAGE_COLOUR = (-1, -1, -1) # Ensure this is different from the background
MESSAGE_WRAPPING_THRESHOLD = 0.8 # Percentage of screen width at which message text gets wrapped
MESSAGE_LETTER_SIZE = 24 # px

# Define sizes of the different visual stimuli
GABOR_SIZE = 5                   # Degrees
LETTER_SIZE = 0.5                # Degrees
FIXATION_SIZE = 0.25             # Degrees
ADAPTATION_FIX_CROSS_SIZE = 0.5  # Degrees

# Used when generating the Gabors/Noise Disk, according to the paper I reference:
DEFAULT_BACKGROUND_LUM = (BG_COLOUR[0] + 1) / 2 # Tries to match stim bg to screen bg
DEFAULT_GABOR_CONTRAST = 1.0 # Max contrast for Gabor
DEFAULT_GABOR_SIGMA_DEG_FACTOR = 5.0 # Sigma as fraction of size (e.g., size / 5)
FREQ_COARSE_CPD = 1.0
FREQ_FINE_CPD = 2.0

# Define the letters to use in the "divert" condition
TARGET_LETTER = "X"
DISTRACTOR_LETTERS = ["Z", "L", "N", "T"]
TARGET_PROB_INCREASE_THRESHOLD = -4 # Number < 0: Specifies a point at which a 2nd 'X' is added to listy of possible
                                    # letters, increasing its chance of showing.


# --- Experiment Parameters ---
# Session timing
MAX_SESSION_TIME = 6 # Minutes - set to 0.25 for quick testing

# Set the min number of standard trials before an oddball can occur:
MIN_STANDARDS = 2

# Number of sessions per each 'attend' and 'divert' attention condition (not considering counterbalancing of oddballs):
NUM_OF_SESSIONS_PER_CONDITION = 1

# Set desired durations for different stimuli and interim periods in seconds.
INTERIM_DURATION = 2.0  # Defines how long should the main stimuli disappear.
MAIN_STIM_DURATION = 0.150 # Refers to the gabor/noise stimuli duration
ATTENTION_DURATION = 0.2 # Duration of fixation/letter chunks and main stim screen time
RESPONSE_DELAY = 10 # The number of "Attention Durations" between possible attend response stimuli - prevents spamming.
ADAPTATION_DURATION = 20 # Seconds - Time given for eyes to adjust to the screen before a session begins (after practice)

# Probabilities
CHANCE_OF_ODDBALL = 0.2
CHANCE_OF_PRIMARY_ODDBALL = 0.75 # sets the threshold over which rare oddballs can occur - percentage
CHANCE_OF_FIXATION_CHANGE = 0.1 # Used in the 'attend' condition where the fixation circle (not letters) is shown

# Practice Session Options
ENABLE_PRACTICE_SESSIONS = True
PRACTICE_CHANCE_OF_FIXATION_CHANGE = 0.4 # As above, but used in practice sessions
ACCEPTABLE_ACCURACY = 0.7
PRACTICE_DURATION = 1 # Minutes



# --- Python Logging Settings ---
log_level_str = "INFO"  # Can be "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"
log_filename = "./data/log"
log_level = getattr(logging, log_level_str.upper(), logging.INFO)
