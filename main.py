import pylink
import psychopy.visual
import psychopy.core
import psychopy.event
import psychopy.gui
import psychopy.monitors
import psychopy.logging
import os
import sys
import time
import datetime as dt
import random
import logging

# # Import config and the graphics library
import config
from EyeLinkCoreGraphicsPsychoPy import EyeLinkCoreGraphicsPsychoPy

# Import the individual functions I made:
import generate_main_stimuli
from calculate_frame_periods import get_nearest_frame
import plan_blocks_and_sessions
from basic_helpers import clear_screen, show_msg, msg_eyetracker
from block_handler import run_block
from run_practice import run_practice


# --- 1. Collect participant info ---
expInfo = {'name': '', 'session': '1'}

# Prompt the participant for their input:
dlg = psychopy.gui.DlgFromDict(dictionary=expInfo, sortKeys=False, title=config.STUDY_NAME)
if not dlg.OK:
    print("User cancelled participant info dialog.")
    psychopy.core.quit()

# Create a unique filename for the EDF:
expInfo['date'] = dt.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
expInfo['expName'] = config.STUDY_NAME
edf_name_string = f"{dt.datetime.now().strftime('%d')}{expInfo['name'][:4]}S{str(expInfo['session'])[:1]}"
edf_filename_host = edf_name_string + ".EDF"


# --- 2. Basic Setup ---
# Create a data folder if it doesn't exist for the log file and the EDF file (generated through the EyeLink host PC).
log_filename = config.log_filename + edf_name_string + ".txt"
if not os.path.exists(config.RESULTS_FOLDER):
    try:
        os.makedirs(config.RESULTS_FOLDER)
        print(f"INFO: Created results directory: {config.RESULTS_FOLDER}")
    except OSError as e:
        print(f"FATAL ERROR: Cannot create results directory {config.RESULTS_FOLDER}: {e}")
        sys.exit()

logging.basicConfig(
    level=config.log_level,
    filename=log_filename,
    filemode="a",  # 'a' for append, 'w' for overwrite each run
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s' # Recommended format
)

logger = logging.getLogger(__name__)
logger.info(f"\nEDF Filename:     {edf_filename_host}")

logger.info(f"Logging level set to: {config.log_level_str}")
logger.info(f"\nLog Filename:     {log_filename}")

logger.info(f"\nParticipant Info: {expInfo}")


# Setup PsychoPy Window
logger.info("Initializing PsychoPy...")
try:
    # Using pixel units is important for EyeLink integration
    win = psychopy.visual.Window(
        size=(config.SCREEN_WIDTH_PX, config.SCREEN_HEIGHT_PX),
        fullscr=True,
        monitor='myMonitor',
        units='pix',
        color=config.BG_COLOUR,
        winType='pyglet',
    )
    win.mouseVisible = False
    logger.info(f"PsychoPy window created ({config.SCREEN_WIDTH_PX}x{config.SCREEN_HEIGHT_PX}).")
except Exception as e:
    logger.critical(f"Failed to create PsychoPy window: {e}")
    sys.exit()

# Calculate the number of frames required for each defined time period (using calculate_frame_periods.py):
interim_frames =   get_nearest_frame(config.INTERIM_DURATION, config.FPS)
main_stim_frames = get_nearest_frame(config.MAIN_STIM_DURATION, config.FPS)
attention_frames = get_nearest_frame(config.ATTENTION_DURATION, config.FPS)

# Pre-set the sessions, their blocks and trials:
run_sessions = []
# num of ses' per condition, x counterbalancing of oddballs x number of attention conditions ('attend' vs 'divert'):
num_sessions = config.NUM_OF_SESSIONS_PER_CONDITION * 2 * 2

logger.info("\n--- Planning Sessions ---")
for i in range(num_sessions):
    logger.info(f"Session {i + 1}:")
    s_blocks, est_dur = plan_blocks_and_sessions.populate_session(
        max_session_time_min=config.MAX_SESSION_TIME,
        attention_duration_sec=config.ATTENTION_DURATION,
        interim_duration_sec=config.INTERIM_DURATION,
        min_standards=config.MIN_STANDARDS,
        chance_of_oddball=config.CHANCE_OF_ODDBALL
    )
    logger.info(f"  Blocks={len(s_blocks)}, Est. Runtime={int(est_dur / 60)}:{round(est_dur % 60,2):05.2f}")
    logger.info(f"  {s_blocks}\n")
    run_sessions.append(s_blocks)

# Randomise session order (Attend vs Divert)
ses_options = [["attend", "attend"], ["divert", "divert"]]
random.shuffle(ses_options)
# Flatten the list
ses_order = [item for sublist in ses_options for item in sublist]
logger.info(f"Session Condition Order: {ses_order}")

# Randomise common vs uncommon oddball assignment (Fine Gabor vs Noise Disk) by shuffling the oddball types,
# then accessing this randomised list via their indexed positions to define the order:
oddball_types = ["fine gabor", "noise disk"]
random.shuffle(oddball_types)
# Repeat the shuffled pattern for 4 sessions
oddball_order = [oddball_types[0], oddball_types[1], oddball_types[0], oddball_types[1]]
logger.info(f"\nCommon Oddball Order: {oddball_order}")



# --- 3. Generate stimuli if needed ---
# A list of dicts detailing the stimuli that need generating:
stim_to_generate = [
    {'type': 'gabor_coarse', 'filename': config.COARSE_GABOR_FILENAME},
    {'type': 'gabor_fine', 'filename': config.FINE_GABOR_FILENAME},
    {'type': 'noise_disk', 'filename': config.NOISE_DISK_FILENAME}
]

# Generate each of the stimuli listed in the above dict:
logger.info("\n--- Checking If Visual Stimuli Are Generated ---")
for stim_info in stim_to_generate:
    stim_path = os.path.join(config.STIMULI_FOLDER, f"{stim_info['filename']}.png")

    if not os.path.exists(stim_path):
        output_path, pix_per_deg = generate_main_stimuli.generate_stimulus(
            stim_type=stim_info['type'],
            filename=stim_info['filename'], # Pass the base filename
            screen_width_px=config.SCREEN_WIDTH_PX,
            screen_width_cm=config.SCREEN_WIDTH_CM,
            view_distance=config.VIEW_DIST_CM,
        )
        logger.info(f"File {stim_info['type']} did not exist - it has been generated and saved to {output_path}.")
    else:
        logger.info(f"File {stim_info['type']} already exists - no need to generate.")

# Create the psychopy stimulus objects for the experiment:
fine_gabor = psychopy.visual.ImageStim(  # Oddball 1 stimulus
    win=win, image=os.path.join(config.STIMULI_FOLDER, f"{config.FINE_GABOR_FILENAME}.png"),
    units="deg",
    size=config.GABOR_SIZE,
    mask="circle"
)
coarse_gabor = psychopy.visual.ImageStim(  # The standard stimulus
    win=win,
    image=os.path.join(config.STIMULI_FOLDER, f"{config.COARSE_GABOR_FILENAME}.png"),
    units="deg",
    size=config.GABOR_SIZE,
    mask="circle"
)
noise_disk = psychopy.visual.ImageStim(  # Oddball 2 stimulus
    win=win,
    image=os.path.join(config.STIMULI_FOLDER, f"{config.NOISE_DISK_FILENAME}.png"),
    units="deg",
    size=config.GABOR_SIZE,
    mask="circle"
)
fixation_circle = psychopy.visual.Circle(
    win=win,
    units="deg",
    size=config.FIXATION_SIZE,
    fillColor=config.STANDARD_COLOUR,
    lineColor=config.STANDARD_COLOUR
)
letter_stim = psychopy.visual.TextStim(
    win=win,
    units="deg",
    alignText="center",
    anchorHoriz="center",
    anchorVert="center",
    color=config.STANDARD_COLOUR,
    text=" ",
    pos=(0, 0),
    height=config.LETTER_SIZE
)
fixation_cross = psychopy.visual.TextStim(
win=win,
    units="deg",
    alignText="center",
    anchorHoriz="center",
    anchorVert="center",
    color=config.STANDARD_COLOUR,
    text="+",
    pos=(0, 0),
    height=config.ADAPTATION_FIX_CROSS_SIZE
)
reusable_message = psychopy.visual.TextStim(
    win=win,
    text="",
    color=config.MESSAGE_COLOUR,
    units='pix',
    pos=(0, 0),
    wrapWidth=config.SCREEN_WIDTH_PX * config.MESSAGE_WRAPPING_THRESHOLD, # Wrap text if long
    height=config.MESSAGE_LETTER_SIZE
)

logger.info("\nPsychoPy visual stimuli created.")



# --- 3. Connect to EyeLink Tracker ---
logger.info("Connecting to EyeLink...")
el_tracker = None
try:
    if config.DUMMY_MODE:
        logger.info("Running in DUMMY MODE")
        el_tracker = pylink.EyeLink(None)
    else:
        logger.info("Attempting connection to 100.1.1.1...")
        el_tracker = pylink.EyeLink("100.1.1.1")
        logger.info("Connection successful.")
except RuntimeError as error:
    logger.critical(f'Could not connect to EyeLink: {error}')
    win.close()
    sys.exit()
except Exception as e:
    logger.critical(f"Unexpected error during connection: {e}")
    win.close()
    sys.exit()



# --- 4. Open EDF File on Host PC ---
# Form a filename for the EDF consisting of the day's date (01-31),
# followed by first 4 chars of name, then S and Session number:
edf_name_string = f"{dt.datetime.now().strftime('%d')}{expInfo['name'][:4]}S{str(expInfo['session'])[:1]}"
edf_filename_host = edf_name_string + ".EDF"

try:
    logger.info(f"Opening EDF file '{edf_filename_host}' on Host PC...")
    el_tracker.openDataFile(edf_name_string) #TODO: Check if I should be using edf_filename_host here
    # Add preamble text (good practice)
    preamble_text = f"RECORDED DURING {config.STUDY_NAME}"
    el_tracker.sendCommand(f"add_file_preamble_text '{preamble_text}'")
    logger.info("EDF file opened and preamble added.")
except RuntimeError as err:
    logger.critical(f'Could not open EDF file on Host PC: {err}')
    if el_tracker.isConnected(): el_tracker.close()
    win.close()
    sys.exit()



# --- 5. Configure Tracker Settings ---
# Based on manual and your setup (EyeLink 1000, likely v4.x software)
logger.info("Configuring tracker...")
try:
    # Put tracker in offline mode
    el_tracker.setOfflineMode()
    pylink.msecDelay(50)

    # Send screen resolution command
    # Using the hardcoded screen dimensions
    el_coords = f"screen_pixel_coords = 0 0 {config.SCREEN_WIDTH_PX - 1} {config.SCREEN_HEIGHT_PX - 1}"
    el_tracker.sendCommand(el_coords)
    logger.info(f"Sent screen coordinates: {el_coords}")
    # Send DISPLAY_COORDS message for DataViewer compatibility
    dv_coords = f"DISPLAY_COORDS 0 0 {config.SCREEN_WIDTH_PX - 1} {config.SCREEN_HEIGHT_PX - 1}"
    el_tracker.sendMessage(dv_coords)
    logger.info(f"Sent DISPLAY_COORDS message: {dv_coords}")

    # Set data types to save in EDF and send over link
    file_sample_flags = 'LEFT,RIGHT,GAZE,AREA,GAZERES,STATUS'  # AREA includes pupil size
    link_sample_flags = 'LEFT,RIGHT,GAZE,GAZERES,AREA,STATUS'  # AREA includes pupil size

    file_event_flags = 'LEFT,RIGHT,FIXATION,SACCADE,BLINK,MESSAGE,BUTTON'
    link_event_flags = 'LEFT,RIGHT,FIXATION,SACCADE,BLINK,BUTTON'

    el_tracker.sendCommand(f"file_sample_data = {file_sample_flags}")
    el_tracker.sendCommand(f"link_sample_data = {link_sample_flags}")
    el_tracker.sendCommand(f"file_event_filter = {file_event_flags}")
    el_tracker.sendCommand(f"link_event_filter = {link_event_flags}")
    logger.info(f"Set data filters. File samples: {file_sample_flags}, Link samples: {link_sample_flags}")

    # Set calibration type (HV9 is common)
    el_tracker.sendCommand("calibration_type = HV9")
    logger.info("Set calibration type to HV9.")

    # Set pupil tracking mode (Centroid might be simpler initially, Ellipse generally better)
    # el_tracker.sendCommand("pupil_size_diameter = YES") # If you prefer diameter over area
    el_tracker.sendCommand(
        "use_ellipse_fitter = NO")  # Start with Centroid? Or YES for Ellipse. Manual p71 recommends Centroid unless occlusion is an issue.
    logger.info("Set pupil fitter to Centroid (use_ellipse_fitter = NO).")

    logger.info("Tracker configuration complete.")

except Exception as e:
    logger.error(f"Failed during tracker configuration: {e}")
    if el_tracker.isConnected(): el_tracker.close()
    win.close()
    sys.exit()



# --- 6. Setup EyeLink Graphics ---
logger.info("Setting up EyeLink graphics...")
try:
    genv = EyeLinkCoreGraphicsPsychoPy(el_tracker, win)
    logger.info(f"Initialized EyeLinkCoreGraphicsPsychoPy: {genv}")

    # Set calibration colors
    foreground_color = (-1, -1, -1)  # Black
    background_color = config.BG_COLOUR
    genv.setCalibrationColors(foreground_color, background_color)


    # Set calibration target type and size
    genv.setTargetType('circle')  # Use simple circle
    genv.setTargetSize(config.CALIBRATION_TARGET_SIZE)
    # genv.setTargetType('picture') # Or use the picture
    # genv.setPictureTarget(os.path.join(config.IMAGES_FOLDER, 'fixTarget.bmp'))

    # Set default sounds
    genv.setCalibrationSounds("", "", "")

    # Register graphics environment
    pylink.openGraphicsEx(genv)
    logger.info("Registered custom graphics environment.")

except Exception as e:
    logger.critical(f"Failed to setup EyeLink graphics: {e}")
    if el_tracker.isConnected(): el_tracker.close()
    win.close()
    sys.exit()



# --- 7. Calibrate Tracker ---
logger.info("Starting calibration...")
psychopy.core.wait(0.5)  # Small pause

# Display instructions
psychopy.visual.TextStim(win, "Press ENTER twice to calibrate", color=(-1, -1, -1)).draw()
win.flip()
psychopy.event.waitKeys(keyList=['return'])

if not config.DUMMY_MODE:
    try:
        logger.info("Entering tracker setup...")
        el_tracker.doTrackerSetup()
        logger.info("Exited tracker setup.")
    except RuntimeError as err:
        logger.error(f'Error during doTrackerSetup: {err}')
        el_tracker.exitCalibration()  # Attempt to exit cleanly
    except Exception as e:
        logger.error(f'Unexpected error during doTrackerSetup: {e}')
        if el_tracker.isConnected(): el_tracker.exitCalibration()
else:
    logger.info("Skipping calibration in Dummy mode.")
    psychopy.visual.TextStim(win, "Dummy Mode: Press Enter to continue", color=(-1, -1, -1)).draw()
    win.flip()
    psychopy.event.waitKeys(keyList=['return'])

# Clear screen after calibration
win.color = config.BG_COLOUR
win.flip()



# --- 8. MAIN LOOP ---
practiced_conditions = set()
delay_countdown = config.RESPONSE_DELAY

# Counters for eye-tracker reporting:
trial_counter = 0

for session_counter, (session_condition, main_oddball) in enumerate(zip(ses_order, oddball_order)):
    logger.info(f"\n===== Preparing Session {session_counter + 1}/{num_sessions} ({session_condition}) =====")

    # Set up the objects for use in the session - these get passed to the session handler function, and so need to be
    # defined here:
    if main_oddball == "fine gabor":
        main_oddball_obj, main_oddball_name = fine_gabor, "fine gabor"
        rare_oddball_obj, rare_oddball_name = noise_disk, "noise disk"
    elif main_oddball == "noise disk":
        main_oddball_obj, main_oddball_name = noise_disk, "noise disk"
        rare_oddball_obj, rare_oddball_name = fine_gabor, "fine gabor"
    else:
        logger.error(f"Unknown oddball type '{main_oddball}'.")
    standard_stimulus_obj, standard_stimulus_name = coarse_gabor, "coarse gabor"

    # Define the fixation object (small central circle that changes colour vs stream of letters in the center):
    if session_condition == "attend":
        fixation_obj = fixation_circle
    elif session_condition == "divert":
        fixation_obj = letter_stim


# ----- Practice Session if needed:
    # Initialise a bool for the while loop. Set it to True to bypass the practice session if set in the config:
    if config.ENABLE_PRACTICE_SESSIONS == True:
        if session_condition not in practiced_conditions: # Needed to avoid inf looping on 2nd session of completed type
            practice_complete = False
        else:
            practice_complete = True
    else:
        practice_complete = True

    # Keep performing the practice until participants demonstrate competency:
    while not practice_complete:
        if session_condition not in practiced_conditions and config.ENABLE_PRACTICE_SESSIONS == True:
            logger.info(f"--- Running Practice for '{session_condition}' ---")
            practice_complete = run_practice(
                practice_condition=session_condition,
                max_duration=config.PRACTICE_DURATION, #in minutes
                attention_duration=config.ATTENTION_DURATION,
                interim_duration=config.INTERIM_DURATION,
                min_standards=config.MIN_STANDARDS,
                oddball_odds=config.CHANCE_OF_ODDBALL,
                norm_colour=config.STANDARD_COLOUR,
                att_colour=config.RESPONSE_COLOUR,
                rare_odd_threshold=config.CHANCE_OF_PRIMARY_ODDBALL,
                win=win,
                standard_stimulus_obj=standard_stimulus_obj,
                main_oddball_obj=main_oddball_obj,
                rare_oddball_obj=rare_oddball_obj,
                standard_stimulus_name=standard_stimulus_name,
                main_oddball_name=main_oddball_name,
                rare_oddball_name=rare_oddball_name,
                fixation_obj=fixation_obj,
                attention_frames=attention_frames,
                main_stim_frames=main_stim_frames,
                interim_frames=interim_frames,
                colour_change_chance=config.PRACTICE_CHANCE_OF_FIXATION_CHANGE,
                target_letter=config.TARGET_LETTER,
                distractor_letters=config.DISTRACTOR_LETTERS,
                accepted_response_accuracy=config.ACCEPTABLE_ACCURACY,
                reusable_message_obj= reusable_message,
                defined_response_delay=config.RESPONSE_DELAY,
                delay_countdown=delay_countdown,
                prob_threshold=config.TARGET_PROB_INCREASE_THRESHOLD,
                session_counter=session_counter,
                experiment_run_number=int(expInfo['session']),
                el_tracker=el_tracker
            )
        if not practice_complete:
            show_msg(
                reusable_message, win,
                text=f"The expected accuracy of your responses was not achieved, please try again'."
                     f"\n\nPress any key to continue.",
                wait_for_keypress=True
            )
        else:
            if int(expInfo['session']) <= 1: # Don't show this message if no practice was done because it's not the first exp run
                show_msg(
                    reusable_message, win,
                    text=f"Practice complete for '{session_condition}'.\n\nPress any key to continue.",
                    wait_for_keypress=True
                )

    # Upon finishing the practice session, mark its condition type as completed:
    practiced_conditions.add(session_condition)
    logger.info(f"--- Practice for '{session_condition}' Complete ---")


# ----- Perform a drift correction prior to the eye-adaptation phase before the start of every session:
    logger.info("\n--- Performing Drift Check between sessions ---")

    # Set targets to the center of the screen:
    target_x = config.SCREEN_WIDTH_PX // 2
    target_y = config.SCREEN_HEIGHT_PX // 2

    if el_tracker.isRecording() != pylink.IN_IDLE_MODE:  # Check if not in idle mode
        logger.info("Ensuring tracker is offline before drift check...")
        el_tracker.setOfflineMode()
        pylink.msecDelay(50)

    # Perform the check:
    try:
        error = el_tracker.doDriftCorrect(target_x, target_y, 1, 1)
        if error == pylink.ESC_KEY:
            logger.info("User requested recalibration (ESC during drift check). Entering setup...")
            el_tracker.doTrackerSetup()  # Re-run calibration if needed
            logger.info("Exited setup after drift check request.")
        elif error != pylink.TRIAL_OK:
            logger.error(f"Drift check unsuccessful (Result Code: {error}). Proceeding anyway.")
        else:
            logger.info("Drift check successful.")

    except RuntimeError as err:
        logger.error(f'Error during doDriftCorrect: {err}')
    except Exception as e:
         logger.error(f'Unexpected error during doDriftCorrect: {e}')

    # Reset the screen when done:
    clear_screen(win)


# ----- Start the Recording ---
    recording_started = False
    try:
        logger.info("Attempting to start recording...")
        # Check recording state before starting (belt-and-suspenders)
        if el_tracker.isRecording() == pylink.TRIAL_OK:
            logger.error("Tracker was already recording? Stopping first.")
            el_tracker.stopRecording()
            pylink.pumpDelay(100)

        error = el_tracker.startRecording(1, 1, 1, 1)  # File samples, file events, link samples, link events
        if error:  # startRecording returns error code, 0 is success
            logger.critical(f"Failed to start recording! Code: {error}")
            raise RuntimeError(f"startRecording error code: {error}")
        recording_started = True
        pylink.pumpDelay(100)  # Wait for the recording to settle
        logger.info("Recording started.")

    except Exception as e:
        logger.critical(f"An error occurred during the trial: {e}")
        # Attempt to stop recording if it started
        if recording_started and el_tracker.isConnected() and el_tracker.isRecording() == pylink.TRIAL_OK:
            logger.error("Attempting to stop recording after trial error...")
            el_tracker.stopRecording()
            logger.error("Recording stopped.")


# ----- Adaptation Period (Runs before every session) ---
    logger.info(f"--- Starting Adaptation Period ({config.ADAPTATION_DURATION}s) ---")

    # Show brief instruction:
    instr_text = (f"Please relax while focusing on the cross.\n"
                  f"The experiment will begin in {config.ADAPTATION_DURATION} seconds.")
    show_msg(reusable_message, win, instr_text, wait_for_keypress=True, timeout_sec=5)
    clear_screen(win)

    # Begin the adaptation period
    start_time = psychopy.core.monotonicClock.getTime()

    # Report the start of the adaptation period to the eye-tracker:
    msg_eyetracker(
        msg_identifier="ADAPTATION_START",
        message=f"T:{start_time:.4f},  Duration:{config.ADAPTATION_DURATION}",
        el_tracker=el_tracker,
        log_msg=True,
        create_var=False
    )

    while psychopy.core.monotonicClock.getTime() < start_time + config.ADAPTATION_DURATION:
        # Draw fixation cross, currently
        fixation_cross.draw()
        win.flip()

    # End the adaptation period by clearing the screen and reporting the ending to the eye-tracker:
    msg_eyetracker(
        msg_identifier="ADAPTATION_END",
        message=f"T:{psychopy.core.monotonicClock.getTime():.4f}",
        el_tracker=el_tracker,
        log_msg=True,
        create_var=False
    )
    clear_screen(win)
    logger.info("--- Adaptation Period Finished ---")


# ----- Session Runner ---
    # Get the list of blocks to run through for this session:
    blocks_in_session = run_sessions[session_counter]

    # Iterate over these blocks, passing each one into this function to run it:
    for block_counter, block in enumerate(blocks_in_session): # block_counter for eye-tracker logging
        logger.info(f"--- Running Session {session_counter + 1}/{num_sessions} Block {block} ---")
        _, _, delay_countdown = run_block(
            block=block,
            condition=session_condition,
            norm_colour=config.STANDARD_COLOUR,
            att_colour=config.RESPONSE_COLOUR,
            rare_odd_threshold=config.CHANCE_OF_PRIMARY_ODDBALL,
            win=win,
            standard_stim_obj=standard_stimulus_obj,
            common_odd_obj=main_oddball_obj,
            rare_odd_obj=rare_oddball_obj,
            standard_stim_name=standard_stimulus_name,
            common_odd_name=main_oddball_name,
            rare_odd_name=rare_oddball_name,
            fixation_obj=fixation_obj,
            attention_frames=attention_frames,
            main_stim_frames=main_stim_frames,
            interim_frames=interim_frames,
            colour_change_chance=config.CHANCE_OF_FIXATION_CHANGE,
            target_letter=config.TARGET_LETTER,
            distractor_letters=config.DISTRACTOR_LETTERS,
            defined_response_delay=config.RESPONSE_DELAY,
            delay_countdown=delay_countdown,
            prob_threshold=config.TARGET_PROB_INCREASE_THRESHOLD,
            session_counter=session_counter,
            block_counter=block_counter,
            el_tracker=el_tracker,
            practice=False
        )


# ----- Stop The Recording ---
    if recording_started:
        try:
            # Check if still recording before stopping
            if el_tracker.isRecording() == pylink.TRIAL_OK:
                logger.info("Stopping recording...")
                pylink.pumpDelay(100)  # Catch final samples/events
                el_tracker.stopRecording()
                logger.info("Recording stopped.")
            else:
                logger.error("Tracker was not recording at the end of the trial loop.")
        except Exception as e:
            logger.error(f"Failed to stop recording cleanly: {e}")


# ----- Break Time ---
    # Offer the participant a break, requiring a key press to move on. Don't offer a break after the final session:
    if session_counter != len(ses_order) -1:
        break_text = (f"Session {session_counter + 1} complete.\n\n"
                      "Take a short break if needed.\n\n"
                      "When you are ready, press any key to continue ")
        clear_screen(win)
        show_msg(reusable_message, win, break_text, wait_for_keypress=True)



# --- 9. Terminate and Retrieve Data ---
logger.info("Terminating task...")
if el_tracker.isConnected():
    # Put tracker in Offline mode
    logger.info("Putting tracker offline...")
    el_tracker.setOfflineMode()
    pylink.msecDelay(500)

    # Close the EDF file on Host PC
    logger.info("Closing EDF file on Host...")
    el_tracker.closeDataFile()

    # Download the EDF file
    try:
        # Create a unique local filename
        time_str = time.strftime("_%Y_%m_%d_%H%M%S", time.localtime())
        local_edf_fname = os.path.join(config.RESULTS_FOLDER, edf_name_string + time_str + '.EDF')
        logger.info(f"Attempting EDF transfer from '{edf_filename_host}' to '{local_edf_fname}'...")
        # Show message on screen
        psychopy.visual.TextStim(win, "Transferring EDF data...", color=(-1, -1, -1)).draw()
        win.flip()
        # Perform transfer
        el_tracker.receiveDataFile(edf_filename_host, local_edf_fname)
        logger.info(f"EDF file transfer successful: '{local_edf_fname}'")
    except RuntimeError as error:
        logger.critical(f'Failed receiving EDF file: {error}')
    except Exception as e:
        logger.critical(f"Unexpected error during EDF transfer: {e}")

    # Close EyeLink connection
    logger.info("Closing EyeLink connection...")
    el_tracker.close()
    logger.info("EyeLink connection closed.")



# --- 10. Cleanup PsychoPy ---
logger.info("Closing PsychoPy window and quitting...")
if win is not None:
    win.close()
psychopy.core.quit()
logger.info("Script finished.")
sys.exit()  # Ensure script exits
