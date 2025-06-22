import random
import math # Needed for populate_session if not using simple integer division
import pylink
import config # Import configuration constants
from psychopy import core, event, logging # Added logging

# Import specific helpers if needed within these functions
# Note: terminate_task is usually called from the main loop or adaptation/practice,
# but might be needed here if an unrecoverable error occurs mid-block.
# Abort_trial is needed if recording stops unexpectedly.
from eyelink_helpers import abort_trial, terminate_task # Import necessary helpers

def create_block(min_standards=config.MIN_STANDARDS, chance_of_oddball=config.CHANCE_OF_ODDBALL):
    """
    Creates a list representing a single block of trials ('s' or 'o').
    Ensures the block starts with min_standards standards and ends with an oddball.
    Args:
        min_standards (int): Minimum number of standard trials at the beginning.
        chance_of_oddball (float): Probability of adding an oddball after min_standards.
    Returns:
        list: A list of strings ('s' or 'o') representing the trial sequence.
    """
    # Makes sure the first block elements are always standard stimuli
    block = ["s" for _ in range(min_standards)]
    # Keep adding elements until we get an oddball
    while True:
        # Generate a random number between 0 and 1
        rand = random.random()

        # If random number is less than chance_of_oddball, add an oddball and break
        if rand < chance_of_oddball:
            block.append("o")
            break
        # Otherwise, add another standard
        else:
            block.append("s")
    return block

def populate_session(max_session_time_min=config.MAX_SESSION_TIME,
                     attention_duration_sec=config.ATTENTION_DURATION,
                     interim_duration_sec=config.INTERIM_DURATION,
                     min_standards=config.MIN_STANDARDS,
                     chance_of_oddball=config.CHANCE_OF_ODDBALL):
    """
    Populates session blocks based on create_block, ensuring total duration
    doesn't exceed MAX_SESSION_TIME. Adds a final block to fill remaining time
    if possible, adhering to block structure.
    Args:
        max_session_time_min (float): Maximum duration of the session in minutes.
        attention_duration_sec (float): Duration of the stimulus/attention phase.
        interim_duration_sec (float): Duration of the interim phase.
        min_standards (int): Min standards per block (passed to create_block).
        chance_of_oddball (float): Oddball chance per block (passed to create_block).
    Returns:
        tuple: (list_of_blocks, estimated_duration_seconds)
    """
    session_blocks = []
    max_ses_seconds = max_session_time_min * 60
    estimated_duration = 0 # Tracks duration of blocks actually added
    trial_duration = attention_duration_sec + interim_duration_sec

    # --- Phase 1: Add random blocks until time limit is approached ---
    while True:
        # Create a new block using the provided parameters
        new_block = create_block(min_standards, chance_of_oddball)
        block_duration = len(new_block) * trial_duration
        potential_total_duration = estimated_duration + block_duration

        # Check if adding this block would exceed the max time
        if potential_total_duration <= max_ses_seconds:
            session_blocks.append(new_block)
            estimated_duration += block_duration
        else:
            # Stop adding random blocks; the next one would exceed the limit
            break

    # --- Phase 2: Calculate remaining time and potentially add a final filler block ---
    remaining_time = max_ses_seconds - estimated_duration

    # Calculate the maximum number of trials that can fit in the remaining time
    max_final_block_length = int(remaining_time // trial_duration) # Integer division

    # Define the minimum valid block length (min_standards 's' + 1 'o')
    min_valid_block_length = min_standards + 1

    # Check if there's enough remaining time for at least the minimum valid block
    if max_final_block_length >= min_valid_block_length:
        # Construct the final block to be exactly max_final_block_length long
        num_standards_in_final = max_final_block_length - 1
        # Ensure it starts with at least min_standards 's' (guaranteed by length check)
        final_block = ["s"] * num_standards_in_final + ["o"]
        session_blocks.append(final_block)
        estimated_duration += len(final_block) * trial_duration
        print(f"  Added filler block of length {len(final_block)} to fill remaining time.")

    return session_blocks, estimated_duration

def get_letter(allow_targets, avoid_letter=None,
               target_letter=config.TARGET_LETTER,
               distractor_letters=config.DISTRACTOR_LETTERS):
    """
    Determines the next letter to show in the divert condition.
    Args:
        allow_targets (bool): Whether the target letter ('X') is allowed.
        avoid_letter (str, optional): A letter to avoid showing if possible (prevents repeats).
        target_letter (str): The target letter (from config).
        distractor_letters (list): List of distractor letters (from config).
    Returns:
        str: The chosen letter.
    """
    possible_choices = distractor_letters.copy()
    if allow_targets:
        possible_choices.append(target_letter)

    # Try to avoid repeating the previous letter
    temp_choices = possible_choices.copy()
    if avoid_letter in temp_choices:
        # Check if removing avoid_letter would leave other options
        if len(temp_choices) > 1:
             temp_choices.remove(avoid_letter)
             possible_choices = temp_choices # Use the list without the avoided letter
        # Else: avoid_letter is the only option left, so we have to repeat it
        # (possible_choices remains unchanged in this case)
    elif len(possible_choices) == 0:
        # This case should theoretically not happen with the current logic,
        # but as a failsafe, reset to full set if somehow empty
        print("ERROR: No possible letters left in get_letter. Resetting choices.")
        possible_choices = distractor_letters.copy()
        if allow_targets: possible_choices.append(target_letter)

    # Final check if list became empty (shouldn't happen)
    if not possible_choices:
         print("CRITICAL ERROR: Letter choice list empty. Returning '?'")
         return "?"

    return random.choice(possible_choices)


# ==============================================================================
#                          ATTEND BLOCK FUNCTION
# ==============================================================================

def attend_block(thisExp, trial_list, common_odd, rare_odd,
                 attention_delay_count, block_idx, session_info, el_tracker, genv,
                 win, filename_full_base, session_folder, edf_fname_short, session_identifier, # Args for terminate_task
                 fixation_circle, coarse_gabor, # Pass stimulus objects
                 attention_frames, main_stim_frames, interim_frames, attention_change_delay_frames): # Pass frame counts
    """
    Runs one block of the 'attend' condition with precise timing logging.
    Handles trial presentation, attention task (fixation color change),
    response collection, and detailed EyeLink logging for each trial event.

    Args:
        thisExp: PsychoPy ExperimentHandler.
        trial_list (list): Sequence of 's' and 'o' for the block.
        common_odd, rare_odd: PsychoPy stimulus objects for oddballs.
        attention_delay_count (int): Counter for delay between attention targets.
        block_idx (int): Zero-based index of the current block.
        session_info (dict): Dictionary containing session details.
        el_tracker: EyeLink tracker instance.
        genv: EyeLink graphics instance.
        win: PsychoPy window instance.
        filename_full_base, session_folder, edf_fname_short, session_identifier: Args for terminate_task.
        fixation_circle, coarse_gabor: Relevant PsychoPy stimulus objects.
        attention_frames, main_stim_frames, interim_frames: Frame counts for durations.
        attention_change_delay_frames: Frame count for delay between attention targets.

    Returns:
        int: Updated attention_delay_count.
    """
    DUMMY_MODE = config.DUMMY_MODE
    block_num = block_idx + 1
    session_type_str = session_info['type']
    common_oddball_str = session_info['common_oddball_name']

    for trial_idx, trial_code in enumerate(trial_list):
        # --- Reset Trial Variables ---
        trial_index_for_edf = f"{block_num}_{trial_idx + 1}"
        trial_num_in_block = trial_idx + 1
        keypress_global_times = []
        trial_aborted_flag = False
        event.clearEvents(eventType='keyboard')
        is_near_oddball = trial_idx >= len(trial_list) - 2
        event_index_in_trial = 0

        # Variables to store precise timings captured during this trial's events
        actual_stim_visual_onset = None
        actual_stim_visual_offset = None
        actual_target_visual_onset = None  # Holds onset time if target appears in stim phase
        actual_target_visual_offset = None  # Holds precise offset time (captured in next chunk)
        last_event_was_target = False  # Track state from previous chunk for offset timing
        oddball_type_this_trial = 'N/A'

        # --- EyeLink: Trial Start ---
        if not DUMMY_MODE:
            try:
                el_tracker.sendMessage(f'TRIALID {trial_index_for_edf}')
                el_tracker.sendMessage(f'!V TRIAL_VAR session_type {session_type_str}')
                el_tracker.sendMessage(f'!V TRIAL_VAR block_num {block_num}')
                el_tracker.sendMessage(f'!V TRIAL_VAR trial_in_block {trial_idx + 1}')
                el_tracker.sendMessage(f'!V TRIAL_VAR common_oddball {common_oddball_str}')
                el_tracker.sendMessage(f'!V TRIAL_VAR trial_code {trial_code}')
                status_msg = f'Trial {trial_index_for_edf} B{block_num} ({session_type_str})'
                el_tracker.sendCommand(f"record_status_message '{status_msg}'")

            except Exception as e:
                logging.warning(f"Could not send TRIALID/VAR message for {trial_index_for_edf}: {e}")

        # ==============================================================
        # --- Event 1: Main Stimulus Presentation Phase              ---
        # ==============================================================
        event_index_in_trial = 0 # Reset for clarity
        event_prep_start_time = core.monotonicClock.getTime() # Approx time prep starts
        current_fixation_color_tuple = config.NORM_FIXATION_COLOUR
        current_fixation_color_str = "black"
        response_expected_this_event = False
        stim_info_logged = False # Track if this event's data row added
        first_flip_time_stim_phase = None
        stim_offset_flip_time = None

        # --- Determine stimuli and attention state for stim phase ---
        if trial_code == "s":
            trial_stim = coarse_gabor
            trial_name_str = 'standard'
            stimulus_presented = config.COARSE_GABOR_FILENAME
            if not DUMMY_MODE:
                try:
                    el_tracker.sendMessage(f"MSG {event_prep_start_time:.4f} TRIAL_TYPE standard") # Approx time
                except:
                    pass

            # Determine fixation color (potential target)
            if not is_near_oddball:
                fixation_rand = random.random()
                if fixation_rand < config.FIXATION_CHANGE_CHANCE and attention_delay_count <= 0:
                    current_fixation_color_tuple = config.RESPOND_FIXATION_COLOUR
                    current_fixation_color_str = "blue"
                    attention_delay_count = attention_change_delay_frames
                    response_expected_this_event = True
                    # Note: PRE_FLIP message sent just before flip below
                else:  # Normal fixation
                    if not DUMMY_MODE:
                        try:
                            el_tracker.sendMessage(f"MSG {event_prep_start_time:.4f} ATTN_STATE FIXATION_BLACK")  # Approx time
                        except:
                            pass
            else:  # Near oddball, always black
                if not DUMMY_MODE:
                    try:
                        el_tracker.sendMessage(f"MSG {event_prep_start_time:.4f} ATTN_STATE FIXATION_BLACK_NEAR_ODDBALL") # Approx time
                    except:
                        pass

        elif trial_code == "o":
            trial_name_str = 'oddball'
            if not DUMMY_MODE:
                try:
                    el_tracker.sendMessage(f"MSG {event_prep_start_time:.4f} TRIAL_TYPE oddball") # Approx time
                except:
                    pass
            # Determine oddball type
            rare_oddball_dice_roll = random.random()
            if rare_oddball_dice_roll < config.CHANCE_OF_PRIMARY_ODDBALL:
                trial_stim = common_odd
                oddball_type_this_trial = session_info['common_oddball_name']
            else:
                trial_stim = rare_odd
                oddball_type_this_trial = session_info['rare_oddball_name']
            stimulus_presented = oddball_type_this_trial
            current_fixation_color_tuple = config.NORM_FIXATION_COLOUR # Fixation always black during oddball
            current_fixation_color_str = "black"
            if not DUMMY_MODE:
                try:
                    el_tracker.sendMessage(f"MSG {event_prep_start_time:.4f} ODDBALL_TYPE {oddball_type_this_trial}") # Approx time
                    el_tracker.sendMessage(f"MSG {event_prep_start_time:.4f} ATTN_STATE FIXATION_BLACK_ODDBALL") # Approx time
                except:
                    pass
        else: # Error case
            logging.error(f"ERROR: Unknown trial type '{trial_code}' in block {block_num}, trial {trial_idx+1}")
            trial_stim = None; trial_name_str = 'error'; stimulus_presented = 'error'
            current_fixation_color_tuple = config.NORM_FIXATION_COLOUR; current_fixation_color_str = "error"
            if not DUMMY_MODE:
                try:
                    el_tracker.sendMessage(f"MSG {event_prep_start_time:.4f} TRIAL_TYPE error")
                except:
                    pass

        fixation_circle.color = current_fixation_color_tuple # Set color before draw loop

        # --- Frame Loop for Stimulus Phase ---
        for frameN in range(attention_frames):
            # Check EyeLink recording status
            if not DUMMY_MODE:
                recording_status = el_tracker.isRecording()
                if recording_status != pylink.TRIAL_OK:
                    logging.error(f"ERROR: Tracker stopped recording mid-trial {trial_index_for_edf}! Code: {recording_status}")
                    try: el_tracker.sendMessage(f"MSG {core.monotonicClock.getTime():.4f} ERROR_TRACKER_STOPPED {recording_status}")
                    except: pass
                    # Don't call abort_trial here, just flag and break to handle after loop
                    trial_aborted_flag = True
                    break # Exit frame loop

            # --- Drawing ---
            stim_drawn_this_frame = False
            if event_index_in_trial == 0 and frameN < main_stim_frames and trial_stim is not None:
                trial_stim.draw()
                stim_drawn_this_frame = True

            fixation_circle.draw() # Always draw fixation
            if attention_delay_count > 0 : attention_delay_count -= 1 # Decrement delay counter

            # --- Intent Messages (Before Flip) ---
            if frameN == 0: # Only send intent messages on the first frame prep
                if stim_drawn_this_frame and actual_stim_visual_onset is None:
                     if not DUMMY_MODE:
                         try:
                             el_tracker.sendMessage(f"MSG {core.monotonicClock.getTime():.4f} PRE_FLIP_STIM_ONSET {stimulus_presented}")
                         except:
                            pass
                if response_expected_this_event and actual_target_visual_onset is None:
                     if not DUMMY_MODE:
                        try:
                            el_tracker.sendMessage(f"MSG {core.monotonicClock.getTime():.4f} PRE_FLIP_TARGET_BLUE_ON")
                        except:
                            pass

            # --- The Flip (Visual Onset) ---
            current_flip_time = win.flip()

            # --- Actual Onset Logging (After Flip) ---
            if frameN == 0:
                first_flip_time_stim_phase = current_flip_time # Record onset of *this phase's visual start*
                # Capture precise visual onset times if they occurred on this frame
                if stim_drawn_this_frame and actual_stim_visual_onset is None:
                    actual_stim_visual_onset = current_flip_time
                    if not DUMMY_MODE:
                        try:
                            el_tracker.sendMessage(f"MSG {actual_stim_visual_onset:.4f} VISUAL_STIM_ONSET {stimulus_presented}")
                        except:
                            pass
                if response_expected_this_event and actual_target_visual_onset is None:
                    actual_target_visual_onset = current_flip_time
                    if not DUMMY_MODE:
                        try:
                            el_tracker.sendMessage(f"MSG {actual_target_visual_onset:.4f} VISUAL_TARGET_BLUE_ON")
                        except:
                            pass

            # --- Stimulus Offset Check & Logging (After Flip) ---
            # If this is the *first frame the main stim is NOT drawn*, its offset occurred on *this* flip
            if event_index_in_trial == 0 and frameN == main_stim_frames and stim_offset_flip_time is None:
                stim_offset_flip_time = current_flip_time # Precise offset time
                actual_stim_visual_offset = stim_offset_flip_time # Store it
                if not DUMMY_MODE:
                    try:
                        el_tracker.sendMessage(f"MSG {stim_offset_flip_time:.4f} VISUAL_STIM_OFFSET {stimulus_presented}")
                    except:
                        pass

            # --- Check responses ---
            # Get keys with timestamps relative to monotonic clock
            keys = event.getKeys(keyList=['space', 'escape'], timeStamped=core.monotonicClock)
            if keys:  # Check if list is not empty
                # keys is now a list of tuples: [('keyname', timestamp), ...]
                for key_name, key_press_time in keys:  # Unpack tuple
                    if key_name == 'space':
                        keypress_global_times.append(key_press_time)  # Append the precise timestamp
                        if not DUMMY_MODE:
                            try:
                                # Log with the precise timestamp
                                el_tracker.sendMessage(f"MSG {key_press_time:.4f} RESPONSE SPACE")
                            except:
                                pass
                    elif key_name == 'escape':
                        # Use the precise timestamp for logging too
                        logging.warning(f"User aborted experiment with ESCAPE during trial {trial_index_for_edf}.")
                        if not DUMMY_MODE:
                            try:
                                el_tracker.sendMessage(f"MSG {key_press_time:.4f} USER_ABORT ESC")
                            except:
                                pass
                        terminate_task(thisExp, filename_full_base, session_folder, edf_fname_short, session_identifier,
                                       win, el_tracker, genv)

        # --- Post-Stimulus Phase Frame Loop ---
        if trial_aborted_flag:
            logging.warning(f"Trial {trial_index_for_edf} aborted due to recording stop. Exiting attend_block.")
            # Attempt to mark the trial as aborted in the EDF if possible
            if not DUMMY_MODE and el_tracker.isConnected():  # Check connection
                try:
                    el_tracker.sendMessage(
                        f"MSG {core.monotonicClock.getTime():.4f} TRIAL_ABORTED_RECORDING_STOP {trial_index_for_edf}")
                    el_tracker.sendMessage(f'TRIAL_RESULT {pylink.ABORT_EXPT}')
                except Exception as e:
                    logging.error(f"Error sending TRIAL_ABORTED message: {e}")
            # Return the current state immediately
            return attention_delay_count

        # --- Log Data Row for Stimulus Phase ---
        if not stim_info_logged: # Log data for the stimulus phase event
            thisExp.addData('block_num', block_num)
            thisExp.addData('trial_num_in_block', trial_num_in_block)
            thisExp.addData('event_index_in_trial', event_index_in_trial)
            thisExp.addData('event_type', "stim_phase")
            thisExp.addData('event_prep_start_time', event_prep_start_time)
            thisExp.addData('event_visual_onset', first_flip_time_stim_phase if first_flip_time_stim_phase else '')
            thisExp.addData('stim_visual_onset', actual_stim_visual_onset if actual_stim_visual_onset else '')
            thisExp.addData('stim_visual_offset', actual_stim_visual_offset if actual_stim_visual_offset else '')
            thisExp.addData('target_visual_onset', actual_target_visual_onset if actual_target_visual_onset else '')
            thisExp.addData('target_visual_offset', '') # Offset logged with next chunk if applicable
            thisExp.addData('is_attention_target', response_expected_this_event)
            thisExp.addData('attention_stim_value', current_fixation_color_str)
            thisExp.addData('keypress_global_times', str(keypress_global_times))
            # Add other identifying info
            thisExp.addData('session_type', session_type_str)
            thisExp.addData('common_oddball', common_oddball_str)
            thisExp.addData('trial_type_code', trial_code)
            thisExp.addData('trial_name', trial_name_str)
            thisExp.addData('stimulus_presented_during_event', stimulus_presented) # What main stim was shown
            thisExp.addData('oddball_type', oddball_type_this_trial) # Specific oddball type if applicable
            thisExp.nextEntry()
            stim_info_logged = True # Mark as logged

        # Reset keypress list for next event chunk
        keypress_global_times = []
        last_event_was_target = response_expected_this_event # Track if this phase ended with target on

        # ==============================================================
        # --- Interim Period (Multiple Chunks)                       ---
        # ==============================================================
        if not DUMMY_MODE:
            try:
                el_tracker.sendMessage(f"MSG {core.monotonicClock.getTime():.4f} INTERIM_START")
            except:
                pass

        for interim_subloop in range(interim_frames // attention_frames):
            event_index_in_trial += 1
            event_prep_start_time = core.monotonicClock.getTime()
            response_expected_this_event = False # Reset for this chunk
            current_fixation_color_tuple = config.NORM_FIXATION_COLOUR # Default to black
            current_fixation_color_str = "black"
            interim_target_visual_onset = None # Track onset within this chunk
            actual_target_visual_offset = None # Reset variable to capture offset timing *in this chunk*
            stim_info_logged = False
            first_flip_time_interim_chunk = None

            # --- Determine Fixation Color for this chunk ---
            # Check if the *previous* event ended with a target, if so, this one MUST be black (offset)
            if last_event_was_target:
                 current_fixation_color_tuple = config.NORM_FIXATION_COLOUR
                 current_fixation_color_str = "black"
                 # Offset message intent will be sent below before flip
            # Otherwise, check if a new target should appear
            elif not is_near_oddball and random.random() < config.FIXATION_CHANGE_CHANCE and attention_delay_count <= 0:
                 current_fixation_color_tuple = config.RESPOND_FIXATION_COLOUR
                 current_fixation_color_str = "blue"
                 attention_delay_count = attention_change_delay_frames
                 response_expected_this_event = True
                 # Onset message intent sent below
            # Else: remains black (already set as default)

            fixation_circle.color = current_fixation_color_tuple

            # --- Frame Loop for Interim Chunk ---
            for frameN in range(attention_frames):
                # Check EyeLink recording status
                if not DUMMY_MODE:
                    recording_status = el_tracker.isRecording()
                    if recording_status != pylink.TRIAL_OK:
                        logging.error(f"ERROR: Tracker stopped recording mid-interim {trial_index_for_edf}! Code: {recording_status}")
                        try: el_tracker.sendMessage(f"MSG {core.monotonicClock.getTime():.4f} ERROR_TRACKER_STOPPED {recording_status}")
                        except: pass
                        trial_aborted_flag = True
                        break # Exit frame loop

                # Draw fixation circle
                fixation_circle.draw()
                if attention_delay_count > 0: attention_delay_count -= 1

                # --- Intent Messages (Before Flip) ---
                if frameN == 0:
                    # If previous chunk ended with target and this one is black, signal offset intent
                    if last_event_was_target and not response_expected_this_event:
                        if not DUMMY_MODE:
                            try:
                                el_tracker.sendMessage(f"MSG {core.monotonicClock.getTime():.4f} PRE_FLIP_TARGET_BLUE_OFF")
                            except:
                               pass
                    # If this chunk is a new target onset
                    elif response_expected_this_event and interim_target_visual_onset is None:
                        if not DUMMY_MODE:
                            try:
                                el_tracker.sendMessage(f"MSG {core.monotonicClock.getTime():.4f} PRE_FLIP_TARGET_BLUE_ON")
                            except:
                                pass
                     # If just normal black fixation state (no target on/off)
                    elif not last_event_was_target and not response_expected_this_event:
                        if not DUMMY_MODE:
                            try:
                                el_tracker.sendMessage(f"MSG {core.monotonicClock.getTime():.4f} ATTN_STATE FIXATION_BLACK") # Approx time
                            except:
                                pass
                # --- The Flip ---
                current_flip_time = win.flip()

                # --- Actual Onset/Offset Logging (After Flip) ---
                if frameN == 0:
                    first_flip_time_interim_chunk = current_flip_time
                    # If previous was target and this isn't, log precise offset time NOW
                    if last_event_was_target and not response_expected_this_event:
                        actual_target_visual_offset = current_flip_time # Precise offset!
                        if not DUMMY_MODE:
                            try:
                                el_tracker.sendMessage(f"MSG {actual_target_visual_offset:.4f} VISUAL_TARGET_BLUE_OFF")
                            except:
                                pass
                    # If this is a new target onset, log precise onset time NOW
                    elif response_expected_this_event and interim_target_visual_onset is None:
                        interim_target_visual_onset = current_flip_time # Precise onset
                        actual_target_visual_onset = interim_target_visual_onset # Store for trial record too
                        if not DUMMY_MODE:
                            try:
                                el_tracker.sendMessage(f"MSG {interim_target_visual_onset:.4f} VISUAL_TARGET_BLUE_ON")
                            except:
                                pass

                # --- Check responses ---
                # Get keys with timestamps relative to monotonic clock
                keys = event.getKeys(keyList=['space', 'escape'], timeStamped=core.monotonicClock)
                if keys:  # Check if list is not empty
                    # keys is now a list of tuples: [('keyname', timestamp), ...]
                    for key_name, key_press_time in keys:  # Unpack tuple
                        if key_name == 'space':
                            keypress_global_times.append(key_press_time)  # Append the precise timestamp
                            if not DUMMY_MODE:
                                try:
                                    # Log with the precise timestamp
                                    el_tracker.sendMessage(f"MSG {key_press_time:.4f} RESPONSE SPACE")
                                except:
                                    pass
                        elif key_name == 'escape':
                            # Use the precise timestamp for logging too
                            logging.warning(f"User aborted experiment with ESCAPE during trial {trial_index_for_edf}.")
                            if not DUMMY_MODE:
                                try:
                                    el_tracker.sendMessage(f"MSG {key_press_time:.4f} USER_ABORT ESC")
                                except:
                                    pass
                            terminate_task(thisExp, filename_full_base, session_folder, edf_fname_short,
                                           session_identifier, win, el_tracker, genv)

            # --- Post-Interim Chunk Frame Loop ---
            if trial_aborted_flag:
                logging.warning(
                    f"Trial {trial_index_for_edf} (Interim) aborted due to recording stop. Exiting attend_block.")
                if not DUMMY_MODE and el_tracker.isConnected():
                    try:
                        el_tracker.sendMessage(
                            f"MSG {core.monotonicClock.getTime():.4f} TRIAL_ABORTED_RECORDING_STOP {trial_index_for_edf}")
                        el_tracker.sendMessage(f'TRIAL_RESULT {pylink.ABORT_EXPT}')
                    except Exception as e:
                        logging.error(f"Error sending TRIAL_ABORTED message: {e}")
                # Return the current state immediately
                return attention_delay_count

            # --- Log Data Row for Interim Chunk ---
            if not stim_info_logged:
                thisExp.addData('block_num', block_num)
                thisExp.addData('trial_num_in_block', trial_num_in_block)
                thisExp.addData('event_index_in_trial', event_index_in_trial)
                thisExp.addData('event_type', "interim_chunk")
                thisExp.addData('event_prep_start_time', event_prep_start_time)
                thisExp.addData('event_visual_onset', first_flip_time_interim_chunk if first_flip_time_interim_chunk else '')
                thisExp.addData('stim_visual_onset', '') # No main stim
                thisExp.addData('stim_visual_offset', '')
                thisExp.addData('target_visual_onset', interim_target_visual_onset if interim_target_visual_onset else '')
                thisExp.addData('target_visual_offset', actual_target_visual_offset if actual_target_visual_offset else '') # Log offset captured at start of this chunk
                thisExp.addData('is_attention_target', response_expected_this_event)
                thisExp.addData('attention_stim_value', current_fixation_color_str)
                thisExp.addData('keypress_global_times', str(keypress_global_times))
                # Add other identifying info
                thisExp.addData('session_type', session_type_str)
                thisExp.addData('common_oddball', common_oddball_str)
                thisExp.addData('trial_type_code', trial_code)
                thisExp.addData('trial_name', trial_name_str)
                thisExp.addData('stimulus_presented_during_event', 'N/A')
                thisExp.addData('oddball_type', 'N/A')
                thisExp.nextEntry()
                stim_info_logged = True

            # Reset state for next chunk
            keypress_global_times = []
            last_event_was_target = response_expected_this_event # Update for next iteration's offset check

    return attention_delay_count  # Return updated delay counter


# ==============================================================================
#                          DIVERT BLOCK FUNCTION
# ==============================================================================

def divert_block(thisExp, trial_list, common_odd, rare_odd,
                 curr_letter, block_idx, session_info, el_tracker, genv,
                 win, filename_full_base, session_folder, edf_fname_short, session_identifier, # Args for terminate_task
                 letter_stim, coarse_gabor, # Pass stimulus objects
                 attention_frames, main_stim_frames, interim_frames): # Pass frame counts
    """
    Runs one block of the 'divert' condition with precise timing logging.
    Handles trial presentation, attention task (letter stream 'X' target),
    response collection, and detailed EyeLink logging for each trial event.

    Args:
        thisExp: PsychoPy ExperimentHandler.
        trial_list (list): Sequence of 's' and 'o' for the block.
        common_odd, rare_odd: PsychoPy stimulus objects for oddballs.
        curr_letter (str): The last letter shown (to avoid repeats).
        block_idx (int): Zero-based index of the current block.
        session_info (dict): Dictionary containing session details.
        el_tracker: EyeLink tracker instance.
        genv: EyeLink graphics instance.
        win: PsychoPy window instance.
        filename_full_base, session_folder, edf_fname_short, session_identifier: Args for terminate_task.
        letter_stim, coarse_gabor: Relevant PsychoPy stimulus objects.
        attention_frames, main_stim_frames, interim_frames: Frame counts for durations.

    Returns:
        str: The last letter shown in this block.
    """
    DUMMY_MODE = config.DUMMY_MODE
    block_num = block_idx + 1
    session_type_str = session_info['type']
    common_oddball_str = session_info['common_oddball_name']
    last_letter_shown = curr_letter # Use a local tracker within the block

    for trial_idx, trial_code in enumerate(trial_list):
        # --- Reset Trial Variables ---
        trial_index_for_edf = f"{block_num}_{trial_idx + 1}"
        trial_num_in_block = trial_idx + 1
        keypress_global_times = []
        trial_aborted_flag = False
        event.clearEvents(eventType='keyboard')
        is_near_oddball = trial_idx >= len(trial_list) - 2
        event_index_in_trial = 0

        # Variables to store precise timings captured during this trial's events
        actual_stim_visual_onset = None
        actual_stim_visual_offset = None
        actual_letter_visual_onset = None # Precise onset for any letter
        actual_target_visual_onset = None # Precise onset specifically for 'X'
        actual_target_visual_offset = None # Precise offset specifically for 'X'
        last_event_was_target = False # Track if previous chunk showed 'X'
        oddball_type_this_trial = 'N/A'

        # --- EyeLink: Trial Start ---
        if not DUMMY_MODE:
            try:
                el_tracker.sendMessage(f'TRIALID {trial_index_for_edf}')
                el_tracker.sendMessage(f'!V TRIAL_VAR session_type {session_type_str}')
                el_tracker.sendMessage(f'!V TRIAL_VAR block_num {block_num}')
                el_tracker.sendMessage(f'!V TRIAL_VAR trial_in_block {trial_idx + 1}')
                el_tracker.sendMessage(f'!V TRIAL_VAR common_oddball {common_oddball_str}')
                el_tracker.sendMessage(f'!V TRIAL_VAR trial_code {trial_code}')
                status_msg = f'Trial {trial_index_for_edf} B{block_num} ({session_type_str})'
                el_tracker.sendCommand(f"record_status_message '{status_msg}'")

            except Exception as e:
                logging.error(f"ERROR during EyeLink setup/start recording for trial {trial_index_for_edf}: {e}")
                if el_tracker and el_tracker.isConnected():
                    if el_tracker.isRecording():
                        try: el_tracker.stopRecording()
                        except: pass # Ignore error if stop fails after start failed
                continue # Skip to next trial

        # ==============================================================
        # --- Event 1: Main Stimulus Presentation Phase              ---
        # ==============================================================
        event_index_in_trial = 0
        event_prep_start_time = core.monotonicClock.getTime()
        letter_presented_this_event = 'N/A'
        is_target_this_event = False # Is the letter shown *this event* the target 'X'?
        stim_info_logged = False
        first_flip_time_stim_phase = None
        stim_offset_flip_time = None
        oddball_type_this_trial = 'N/A' # Initialize

        # --- Determine stimuli and attention state ---
        if trial_code == "s":
            trial_stim = coarse_gabor
            trial_name_str = 'standard'
            stimulus_presented = config.COARSE_GABOR_FILENAME
            if not DUMMY_MODE:
                try:
                    el_tracker.sendMessage(f"MSG {event_prep_start_time:.4f} TRIAL_TYPE standard")
                except:
                    pass
            allow_targets_now = not is_near_oddball
            letter_to_show = get_letter(allow_targets=allow_targets_now, avoid_letter=last_letter_shown)

        elif trial_code == "o":
            trial_name_str = 'oddball'
            if not DUMMY_MODE:
                try:
                    el_tracker.sendMessage(f"MSG {event_prep_start_time:.4f} TRIAL_TYPE oddball")
                except:
                    pass
            rare_oddball_dice_roll = random.random()
            if rare_oddball_dice_roll < config.CHANCE_OF_PRIMARY_ODDBALL:
                trial_stim = common_odd
                oddball_type_this_trial = session_info['common_oddball_name']
            else:
                trial_stim = rare_odd
                oddball_type_this_trial = session_info['rare_oddball_name']
            stimulus_presented = oddball_type_this_trial
            if not DUMMY_MODE:
                try:
                    el_tracker.sendMessage(f"MSG {event_prep_start_time:.4f} ODDBALL_TYPE {oddball_type_this_trial}")
                except:
                    pass
            letter_to_show = get_letter(allow_targets=False, avoid_letter=last_letter_shown) # No targets during oddball

        else: # Error case
            logging.error(f"ERROR: Unknown trial type '{trial_code}' in block {block_num}, trial {trial_idx+1}")
            trial_stim = None; trial_name_str = 'error'; stimulus_presented = 'error'; letter_to_show = '?'
            if not DUMMY_MODE:
                try:
                    el_tracker.sendMessage(f"MSG {event_prep_start_time:.4f} TRIAL_TYPE error")
                except:
                    pass

        last_letter_shown = letter_to_show # Update tracker for next get_letter call
        letter_stim.text = letter_to_show
        letter_stim.color = config.LETTER_COLOUR # Ensure color is set
        letter_presented_this_event = letter_to_show
        is_target_this_event = (letter_to_show == config.TARGET_LETTER)

        # --- Frame Loop for Stimulus Phase ---
        for frameN in range(attention_frames):
            # Check EyeLink recording status
            if not DUMMY_MODE:
                recording_status = el_tracker.isRecording()
                if recording_status != pylink.TRIAL_OK:
                    logging.error(f"ERROR: Tracker stopped recording mid-trial {trial_index_for_edf}! Code: {recording_status}")
                    try: el_tracker.sendMessage(f"MSG {core.monotonicClock.getTime():.4f} ERROR_TRACKER_STOPPED {recording_status}")
                    except: pass
                    trial_aborted_flag = True
                    break # Exit frame loop

            # --- Drawing ---
            stim_drawn_this_frame = False
            if event_index_in_trial == 0 and frameN < main_stim_frames and trial_stim is not None:
                trial_stim.draw()
                stim_drawn_this_frame = True
            letter_stim.draw() # Always draw letter stimulus

            # --- Intent Messages (Before Flip) ---
            if frameN == 0:
                # Stim onset intent
                if stim_drawn_this_frame and actual_stim_visual_onset is None:
                    if not DUMMY_MODE:
                        try:
                            el_tracker.sendMessage(f"MSG {core.monotonicClock.getTime():.4f} PRE_FLIP_STIM_ONSET {stimulus_presented}")
                        except:
                            pass
                # Letter onset intent (always happens on frame 0 of chunk)
                if actual_letter_visual_onset is None:
                    if not DUMMY_MODE:
                        try:
                            el_tracker.sendMessage(f"MSG {core.monotonicClock.getTime():.4f} PRE_FLIP_LETTER_ONSET {letter_presented_this_event}")
                        except:
                            pass
                # Target X onset intent (only if it's an X)
                if is_target_this_event and actual_target_visual_onset is None:
                    if not DUMMY_MODE:
                        try:
                            el_tracker.sendMessage(f"MSG {core.monotonicClock.getTime():.4f} PRE_FLIP_TARGET_X_ON")
                        except:
                            pass

            # --- The Flip ---
            current_flip_time = win.flip()

            # --- Actual Onset Logging (After Flip) ---
            if frameN == 0:
                first_flip_time_stim_phase = current_flip_time # Record onset of this phase's visuals
                # Log precise letter onset time
                actual_letter_visual_onset = current_flip_time
                if not DUMMY_MODE:
                    try:
                        el_tracker.sendMessage(f"MSG {actual_letter_visual_onset:.4f} VISUAL_LETTER_ONSET {letter_presented_this_event}")
                    except:
                        pass
                # Log precise stim onset time if applicable
                if stim_drawn_this_frame and actual_stim_visual_onset is None:
                    actual_stim_visual_onset = current_flip_time
                    if not DUMMY_MODE:
                        try:
                            el_tracker.sendMessage(f"MSG {actual_stim_visual_onset:.4f} VISUAL_STIM_ONSET {stimulus_presented}")
                        except:
                            pass
                # Log precise target X onset time if applicable
                if is_target_this_event and actual_target_visual_onset is None:
                    actual_target_visual_onset = current_flip_time
                    if not DUMMY_MODE:
                        try:
                            el_tracker.sendMessage(f"MSG {actual_target_visual_onset:.4f} VISUAL_TARGET_X_ON")
                        except:
                            pass

            # --- Stimulus Offset Check & Logging (After Flip) ---
            if event_index_in_trial == 0 and frameN == main_stim_frames and stim_offset_flip_time is None:
                stim_offset_flip_time = current_flip_time # Precise offset time
                actual_stim_visual_offset = stim_offset_flip_time # Store it
                if not DUMMY_MODE:
                    try:
                        el_tracker.sendMessage(f"MSG {stim_offset_flip_time:.4f} VISUAL_STIM_OFFSET {stimulus_presented}")
                    except:
                        pass

            # --- Check responses ---
            # Get keys with timestamps relative to monotonic clock
            keys = event.getKeys(keyList=['space', 'escape'], timeStamped=core.monotonicClock)
            if keys:  # Check if list is not empty
                # keys is now a list of tuples: [('keyname', timestamp), ...]
                for key_name, key_press_time in keys:  # Unpack tuple
                    if key_name == 'space':
                        keypress_global_times.append(key_press_time)  # Append the precise timestamp
                        if not DUMMY_MODE:
                            try:
                                # Log with the precise timestamp
                                el_tracker.sendMessage(f"MSG {key_press_time:.4f} RESPONSE SPACE")
                            except:
                                pass
                    elif key_name == 'escape':
                        # Use the precise timestamp for logging too
                        logging.warning(f"User aborted experiment with ESCAPE during trial {trial_index_for_edf}.")
                        if not DUMMY_MODE:
                            try:
                                el_tracker.sendMessage(f"MSG {key_press_time:.4f} USER_ABORT ESC")
                            except:
                                pass
                        terminate_task(thisExp, filename_full_base, session_folder, edf_fname_short, session_identifier,
                                       win, el_tracker, genv)

        # --- Post-Stimulus Phase Frame Loop ---
        if trial_aborted_flag:
            logging.warning(f"Trial {trial_index_for_edf} aborted due to recording stop. Exiting divert_block.")
            # Attempt to mark the trial as aborted in the EDF if possible
            if not DUMMY_MODE and el_tracker.isConnected():  # Check connection
                try:
                    el_tracker.sendMessage(
                        f"MSG {core.monotonicClock.getTime():.4f} TRIAL_ABORTED_RECORDING_STOP {trial_index_for_edf}")
                    el_tracker.sendMessage(f'TRIAL_RESULT {pylink.ABORT_EXPT}')
                except Exception as e:
                    logging.error(f"Error sending TRIAL_ABORTED message: {e}")
            # Return the current state immediately
            return last_letter_shown  # Use the most recent letter shown in this block

        # --- Log Data Row for Stimulus Phase ---
        if not stim_info_logged:
            thisExp.addData('block_num', block_num)
            thisExp.addData('trial_num_in_block', trial_num_in_block)
            thisExp.addData('event_index_in_trial', event_index_in_trial)
            thisExp.addData('event_type', "stim_phase")
            thisExp.addData('event_prep_start_time', event_prep_start_time)
            thisExp.addData('event_visual_onset', first_flip_time_stim_phase if first_flip_time_stim_phase else '')
            thisExp.addData('stim_visual_onset', actual_stim_visual_onset if actual_stim_visual_onset else '')
            thisExp.addData('stim_visual_offset', actual_stim_visual_offset if actual_stim_visual_offset else '')
            thisExp.addData('letter_visual_onset', actual_letter_visual_onset if actual_letter_visual_onset else '')
            thisExp.addData('target_visual_onset', actual_target_visual_onset if actual_target_visual_onset else '')
            thisExp.addData('target_visual_offset', '') # Offset logged with next event chunk
            thisExp.addData('is_attention_target', is_target_this_event)
            thisExp.addData('attention_stim_value', letter_presented_this_event)
            thisExp.addData('keypress_global_times', str(keypress_global_times))
            # Add other identifying info
            thisExp.addData('session_type', session_type_str)
            thisExp.addData('common_oddball', common_oddball_str)
            thisExp.addData('trial_type_code', trial_code)
            thisExp.addData('trial_name', trial_name_str)
            thisExp.addData('stimulus_presented_during_event', stimulus_presented)
            thisExp.addData('oddball_type', oddball_type_this_trial)
            thisExp.nextEntry()
            stim_info_logged = True

        # Reset keypress list for next event chunk
        keypress_global_times = []
        last_event_was_target = is_target_this_event # Track if 'X' was just shown

        # ==============================================================
        # --- Interim Period (Multiple Chunks)                       ---
        # ==============================================================
        if not DUMMY_MODE:
            try:
                el_tracker.sendMessage(f"MSG {core.monotonicClock.getTime():.4f} INTERIM_START")
            except:
                pass

        for interim_subloop in range(interim_frames // attention_frames):
            event_index_in_trial += 1
            event_prep_start_time = core.monotonicClock.getTime()
            is_target_this_event = False # Reset for this chunk
            interim_letter_visual_onset = None
            interim_target_visual_onset = None
            actual_target_visual_offset = None # Reset offset captured flag
            stim_info_logged = False
            first_flip_time_interim_chunk = None

            # --- Determine Letter for this chunk ---
            allow_targets_now = not is_near_oddball
            letter_to_show = get_letter(allow_targets=allow_targets_now, avoid_letter=last_letter_shown)
            last_letter_shown = letter_to_show # Update tracker
            letter_stim.text = letter_to_show
            letter_presented_this_event = letter_to_show
            is_target_this_event = (letter_to_show == config.TARGET_LETTER)

            # --- Frame Loop for Interim Chunk ---
            for frameN in range(attention_frames):
                 # Check EyeLink recording status
                if not DUMMY_MODE:
                    recording_status = el_tracker.isRecording()
                    if recording_status != pylink.TRIAL_OK:
                        logging.error(f"ERROR: Tracker stopped recording mid-interim {trial_index_for_edf}! Code: {recording_status}")
                        try: el_tracker.sendMessage(f"MSG {core.monotonicClock.getTime():.4f} ERROR_TRACKER_STOPPED {recording_status}")
                        except: pass
                        trial_aborted_flag = True
                        break # Exit frame loop

                # Draw letter stimulus
                letter_stim.draw()

                # --- Intent Messages (Before Flip) ---
                if frameN == 0:
                    # Log offset intent for previous X if needed
                    if last_event_was_target and not is_target_this_event:
                        if not DUMMY_MODE:
                            try:
                                el_tracker.sendMessage(f"MSG {core.monotonicClock.getTime():.4f} PRE_FLIP_TARGET_X_OFF")
                            except:
                                pass
                    # Log onset intent for new letter
                    if interim_letter_visual_onset is None:
                        if not DUMMY_MODE:
                            try:
                                el_tracker.sendMessage(f"MSG {core.monotonicClock.getTime():.4f} PRE_FLIP_LETTER_ONSET {letter_presented_this_event}")
                            except:
                                pass
                    # Log onset intent for new X
                    if is_target_this_event and interim_target_visual_onset is None:
                        if not DUMMY_MODE:
                            try:
                                el_tracker.sendMessage(f"MSG {core.monotonicClock.getTime():.4f} PRE_FLIP_TARGET_X_ON")
                            except:
                                pass

                # --- The Flip ---
                current_flip_time = win.flip()

                # --- Actual Onset/Offset Logging (After Flip) ---
                if frameN == 0:
                    first_flip_time_interim_chunk = current_flip_time
                    # Log precise letter onset
                    interim_letter_visual_onset = current_flip_time
                    if not DUMMY_MODE:
                        try:
                            el_tracker.sendMessage(f"MSG {interim_letter_visual_onset:.4f} VISUAL_LETTER_ONSET {letter_presented_this_event}")
                        except:
                            pass

                    # If previous was target 'X' and this isn't, log precise offset
                    if last_event_was_target and not is_target_this_event:
                        actual_target_visual_offset = current_flip_time # Precise offset
                        if not DUMMY_MODE:
                            try:
                                el_tracker.sendMessage(f"MSG {actual_target_visual_offset:.4f} VISUAL_TARGET_X_OFF")
                            except:
                                pass
                    # If this is a new target 'X' onset
                    elif is_target_this_event and interim_target_visual_onset is None:
                        interim_target_visual_onset = current_flip_time # Precise onset
                        actual_target_visual_onset = interim_target_visual_onset # Store for trial record
                        if not DUMMY_MODE:
                            try:
                                el_tracker.sendMessage(f"MSG {interim_target_visual_onset:.4f} VISUAL_TARGET_X_ON")
                            except:
                                pass

                # --- Check responses ---
                    # Get keys with timestamps relative to monotonic clock
                keys = event.getKeys(keyList=['space', 'escape'], timeStamped=core.monotonicClock)
                if keys:  # Check if list is not empty
                    # keys is now a list of tuples: [('keyname', timestamp), ...]
                    for key_name, key_press_time in keys:  # Unpack tuple
                        if key_name == 'space':
                            keypress_global_times.append(key_press_time)  # Append the precise timestamp
                            if not DUMMY_MODE:
                                try:
                                    # Log with the precise timestamp
                                    el_tracker.sendMessage(f"MSG {key_press_time:.4f} RESPONSE SPACE")
                                except:
                                    pass
                        elif key_name == 'escape':
                            # Use the precise timestamp for logging too
                            logging.warning(f"User aborted experiment with ESCAPE during trial {trial_index_for_edf}.")
                            if not DUMMY_MODE:
                                try:
                                    el_tracker.sendMessage(f"MSG {key_press_time:.4f} USER_ABORT ESC")
                                except:
                                    pass
                            terminate_task(thisExp, filename_full_base, session_folder, edf_fname_short,
                                           session_identifier, win, el_tracker, genv)

            # --- Post-Interim Chunk Frame Loop ---
            if trial_aborted_flag:
                logging.warning(
                    f"Trial {trial_index_for_edf} (Interim) aborted due to recording stop. Exiting divert_block.")
                if not DUMMY_MODE and el_tracker.isConnected():
                    try:
                        el_tracker.sendMessage(
                            f"MSG {core.monotonicClock.getTime():.4f} TRIAL_ABORTED_RECORDING_STOP {trial_index_for_edf}")
                        el_tracker.sendMessage(f'TRIAL_RESULT {pylink.ABORT_EXPT}')
                    except Exception as e:
                        logging.error(f"Error sending TRIAL_ABORTED message: {e}")
                # Return the current state immediately
                return last_letter_shown  # Use the most recent letter shown in this block

            # --- Log Data Row for Interim Chunk ---
            if not stim_info_logged:
                thisExp.addData('block_num', block_num)
                thisExp.addData('trial_num_in_block', trial_num_in_block)
                thisExp.addData('event_index_in_trial', event_index_in_trial)
                thisExp.addData('event_type', "interim_chunk")
                thisExp.addData('event_prep_start_time', event_prep_start_time)
                thisExp.addData('event_visual_onset', first_flip_time_interim_chunk if first_flip_time_interim_chunk else '')
                thisExp.addData('stim_visual_onset', '') # No main stim
                thisExp.addData('stim_visual_offset', '')
                thisExp.addData('letter_visual_onset', interim_letter_visual_onset if interim_letter_visual_onset else '')
                thisExp.addData('target_visual_onset', interim_target_visual_onset if interim_target_visual_onset else '')
                thisExp.addData('target_visual_offset', actual_target_visual_offset if actual_target_visual_offset else '')
                thisExp.addData('is_attention_target', is_target_this_event)
                thisExp.addData('attention_stim_value', letter_presented_this_event)
                thisExp.addData('keypress_global_times', str(keypress_global_times))
                 # Add other identifying info
                thisExp.addData('session_type', session_type_str)
                thisExp.addData('common_oddball', common_oddball_str)
                thisExp.addData('trial_type_code', trial_code)
                thisExp.addData('trial_name', trial_name_str)
                thisExp.addData('stimulus_presented_during_event', 'N/A')
                thisExp.addData('oddball_type', 'N/A')
                thisExp.nextEntry()
                stim_info_logged = True

            # Reset state for next chunk
            keypress_global_times = []
            last_event_was_target = is_target_this_event # Update for next offset check

    return last_letter_shown  # Return updated delay counter


def get_nearest_frame(desired_duration_sec, fps=config.FPS): # Added fps arg with default
    """Calculates the number of frames for a duration."""
    if fps <= 0:
        print("Error: FPS must be positive.")
        return 0
    if desired_duration_sec < 0:
        print(f"Warning: Negative duration ({desired_duration_sec}s). Returning 0.")
        return 0
    ideal_frames = desired_duration_sec * float(fps)
    n_frames = int(round(ideal_frames))
    # actual_duration_sec = n_frames / float(fps) # Can uncomment if needed
    return n_frames
