import random
import psychopy.event
import psychopy.core
from numpy import arange
from basic_helpers import msg_eyetracker
import pylink
import logging

logger = logging.getLogger(__name__)

def get_letter(allow_target, target_letter, distractor_letters, increase_target_prob_threshold, delay_countdown,
               avoid_letter=None):
    """
    Determines the next letter to show in the divert condition.
    Args:
        allow_target (bool): Whether the target letter ('X') is allowed.
        target_letter (str): The target letter that a participant would respond to.
        distractor_letters (list): List of distractor letters that would not require a response.
        avoid_letter (str, optional): A letter to avoid showing if possible (prevents repeats if passing prior letter)
    Returns:
        str: The chosen letter.
    """
    possible_choices = distractor_letters.copy()
    if allow_target:
        possible_choices.append(target_letter)
        # Add a 2nd target if the delay countdown has exceeded the threshold, thereby increasing its chance of showing.
        if delay_countdown <= increase_target_prob_threshold:
            possible_choices.append(target_letter)

    temp_choices = possible_choices.copy()

    # Avoid repeating the previous letter by removing it from the list of options:
    if avoid_letter in temp_choices:
        temp_choices.remove(avoid_letter)
        possible_choices = temp_choices # Use the list without the avoided letter

    return random.choice(possible_choices)



# Repeatable code that sets either the fixation circle's colour or the fixation letter, depending on the condition
# passed, the chance of change (colour), and the proximity of the current trial to a past or future oddball trial.
def determine_attention_stimulus(
        condition, trial_idx, acceptable_target_idxs, fixation_obj, norm_colour, att_colour, colour_change_chance,
        target_letter, distractor_letters, n_attention_targets, defined_response_delay, delay_countdown, prob_threshold
):
    # Create a bool that swaps to True only if the fixation stimulus becomes a target stimulus:
    is_att_target = False
    letter_used = ""

    # Set the fixation object's parameters before drawing it ('circle' vs 'letter' depending on condition):
    if condition == "attend":
        # Check if a colour change is allowed based on trial proximity to an oddball:
        if trial_idx not in acceptable_target_idxs:
            fixation_obj.color = norm_colour  # This should never be a response colour if near an oddball trial
        elif delay_countdown > 0: # This both adds a delay between targets and resets the colour after a target.
            fixation_obj.color = norm_colour
        else:
            # Randomly determine if a colour change should occur based on the random chance threshold:
            if colour_change_chance > random.random():
                fixation_obj.color = att_colour
                n_attention_targets += 1 # Used to verify a practice session has been responded to sufficiently.
                is_att_target = True # Used outside the function, mainly for stimulus reporting to the eye-tracker.
                delay_countdown = defined_response_delay + 1  # Reset the delay countdown to prevent spamming of targets
            else:
                fixation_obj.color = norm_colour

    elif condition == "divert":
        # Check if a target letter is allowed based on trial proximity to an oddball:
        if trial_idx not in acceptable_target_idxs:
            fixation_obj.text = get_letter(
                avoid_letter=fixation_obj.text, target_letter=target_letter,
                distractor_letters=distractor_letters, allow_target=False,
                increase_target_prob_threshold=prob_threshold, delay_countdown=delay_countdown
            )
        elif delay_countdown >= 0:
            fixation_obj.text = get_letter(
                avoid_letter=fixation_obj.text, target_letter=target_letter,
                distractor_letters=distractor_letters, allow_target=False,
                increase_target_prob_threshold=prob_threshold, delay_countdown=delay_countdown
            )
        else: # ALLOW TARGETS:
            fixation_obj.text = get_letter(
                avoid_letter=fixation_obj.text, target_letter=target_letter,
                distractor_letters=distractor_letters, allow_target=True,
                increase_target_prob_threshold=prob_threshold, delay_countdown=delay_countdown
            )

        if fixation_obj.text == target_letter:
            n_attention_targets += 1 # Used to verify a practice session has been responded to sufficiently.
            is_att_target = True  # Used outside the function, mainly for stimulus reporting to the eye-tracker.
            delay_countdown = 2 + 1 # Reset the delay countdown to prevent spamming of targets:
                                    # 1st num is num of letters before the next target can occur. TODO: Add to configs
        letter_used = fixation_obj.text

    # Reduce the delay countdown - this is done even when a target has been set as delay_countdown resets are done
    # so using defined_response_delay + 1, thereby offsetting this first reduction:
    delay_countdown -= 1

    return fixation_obj, n_attention_targets, delay_countdown, is_att_target, letter_used



def run_block(
        block, condition, norm_colour, att_colour, rare_odd_threshold, win,
        standard_stim_obj, common_odd_obj, rare_odd_obj, # The Psychopy stimulus objects for the main visual stimuli
        standard_stim_name, common_odd_name, rare_odd_name, # The names of the stimuli (strs) used for logging
        fixation_obj, # The psychopy object for either the fixation circle or the letters (attend vs divert conditions)
        attention_frames, main_stim_frames, interim_frames, # The durations of each trial section (measured in frames)
        colour_change_chance, target_letter, distractor_letters, defined_response_delay, delay_countdown,
        prob_threshold, session_counter, block_counter,
        el_tracker,
        practice=False, # If this is passed as True, then the logging will be limited or altered.
):
    n_attention_targets = 0
    n_attention_responses = 0

    # Report the start of the block to the eye-tracker if it's not a practise session:
    if not practice:
        msg_eyetracker(
            msg_identifier="BLOCK_START",
            message=f"{session_counter+1}_{block_counter+1}",
            el_tracker=el_tracker,
            log_msg=True,
            create_var=False
        )

    # --- Main Loop through the block ---
    for trial_counter, trial_type in enumerate(block):

        # Report the start of the trial top the eye-tracker if it's not a practise session:
        if not practice:
            msg_eyetracker(
                msg_identifier="TRIALID",
                message=f"{session_counter+1}_{block_counter+1}_{trial_counter+1}, "
                        f"T:{psychopy.core.monotonicClock.getTime():.4f}, Type: {trial_type}",
                el_tracker=el_tracker,
                log_msg=True,
                create_var=True
            )

        # Variable setup:
        keypress_times = [] # Used to store the monotonic timings of all keypresses

        # Determine which trials within a block a target attention stimulus (colour-changing circle or a target letter)
        # can occur on - avoids trials that immediately precedes or follow an oddball:
        acceptable_target_idxs = arange(1, len(block) - 2)

        # ==============================================================
        # --- Event 1: Main Stimulus Presentation Phase              ---
        # ==============================================================

        # Determine the trial type:
        if trial_type == "s":
            trial_stim, standard_stim_name = standard_stim_obj, standard_stim_name

        elif trial_type == "o":
            # Randomly decide on the oddball stimulus (common vs rare) based on random number generation and threshold:
            if random.random() > rare_odd_threshold:
                trial_stim, oddball_name = rare_odd_obj, rare_odd_name
            else:
                trial_stim, oddball_name = common_odd_obj, common_odd_name

        else:
            logger.error(f"Unknown trial type defined in the block: {trial_type}")

        # Set the fixation object's parameters before drawing it ('circle' vs 'letter' depending on condition).
        # This needs to be outside the stim-presentation loop as it should occur once, presenting only the resultant
        # stimulus throughout this portion. If placed within, it would make a new choice every frame, spamming changes:
        fixation_obj, n_attention_targets, delay_countdown, is_att_target, att_letter = determine_attention_stimulus(
            condition, trial_counter, acceptable_target_idxs, fixation_obj, norm_colour, att_colour, colour_change_chance,
            target_letter, distractor_letters, n_attention_targets, defined_response_delay, delay_countdown,
            prob_threshold
        )

        # --- Main Loop for this stimulus-presentation section ---
        for frameN in range(attention_frames):

            # Report an error if the eye-tracker stops recording for some reason if in a practise session:
            if not practice:
                eyelink_status = el_tracker.isRecording()
                if eyelink_status != pylink.TRIAL_OK:
                    logger.error(f"Eye-tracker recording has stopped unexpectedly. Code: {eyelink_status}")
                # else:
                #     logger.info(f"MSG:   Eye-tracker seems to be recording fine.         Code: {eyelink_status}")

            # Draw the main visual object for its own set duration (less than the full stim window):
            if frameN < main_stim_frames:
                trial_stim.draw()

            # Draw the object for the attention task's fixation object for the full period of attention_frames:
            fixation_obj.draw()

            # Flip the window to proceed through the loop:
            current_flip_time = win.flip()

            # Report the main and fixation stimuli onset times to the eye-tracker if not a practise session:
            # Main Stimulus:
            if not practice and frameN == 0:
                msg_eyetracker(
                    msg_identifier="MAIN_STIM_ONSET",
                    message=f"{session_counter+1}_{block_counter+1}_{trial_counter+1}, "
                            f"T:{current_flip_time:.4f}, Type: {trial_type}, "
                            f"Stim: {standard_stim_name if trial_type == 's' else oddball_name}",
                    el_tracker=el_tracker,
                    log_msg=True,
                    create_var=False
                )
            # Fixation Stimulus:
                msg_eyetracker(
                    msg_identifier="FIXATION_STIM_ONSET",
                    message=f"{session_counter+1}_{block_counter+1}_{trial_counter+1}, "
                            f"T:{current_flip_time:.4f}, Type: {trial_type}, "
                            f"Attention_type: {'Target' if is_att_target else 'Normal'}, "
                            f"Letter: {att_letter if att_letter != '' else 'None'}",
                    el_tracker=el_tracker,
                    log_msg=True,
                    create_var=False
                )

            # Get keyboard responses after the flip (The earliest time that participants could respond is after
            # the first flip):
            keys = psychopy.event.getKeys(timeStamped=psychopy.core.monotonicClock)
            if keys:
                for key_name, key_press_time in keys:
                    # Report SPACES:
                    if key_name == 'space':
                        keypress_times.append(key_press_time)  # Append the precise timestamp
                        n_attention_responses += 1

                        # Report the keypress to the eye-tracker if not a practise session:
                        if not practice:
                            msg_eyetracker(
                                msg_identifier="KEY_RESPONSE",
                                message=f"{session_counter+1}_{block_counter+1}_{trial_counter+1}, "
                                        f"T:{key_press_time:.4f}, Key: {key_name}",
                                el_tracker=el_tracker,
                                log_msg=True,
                                create_var=False
                            )
                    else:
                        # Report other keys pressed:
                        keypress_times.append(key_press_time)
                        if not practice:
                            msg_eyetracker(
                                msg_identifier="UNEXPECTED_KEY_RESPONSE",
                                message=f"{session_counter + 1}_{block_counter + 1}_{trial_counter + 1}, "
                                        f"T:{key_press_time:.4f}, Key: {key_name}",
                                el_tracker=el_tracker,
                                log_msg=True,
                                create_var=False
                            )
                    #TODO: Add Esc option that terminates the task safely.

            # Report the main stimulus offset times to the eye-tracker if not a practise session:
            if not practice and frameN == main_stim_frames:
                msg_eyetracker(
                    msg_identifier="MAIN_STIM_OFFSET",
                    message=f"{session_counter+1}_{block_counter+1}_{trial_counter+1}, "
                            f"T:{current_flip_time:.4f}, Type: {trial_type}, "
                            f"Stim: {standard_stim_name if trial_type == 's' else oddball_name}",
                    el_tracker=el_tracker,
                    log_msg=True,
                    create_var=False
                )
            # Reset the keypress list for the next part of the trial:
            keypress_global_times = []

        # ===============================================================
        # --- Interim Period (Multiple Chunks of 'attention periods') ---
        # ===============================================================

        # Report the start of the interim period to the eye-tracker if it's not a practise session:
        if not practice:
            msg_eyetracker(
                msg_identifier="INTERIM_START",
                message=f"{session_counter+1}_{block_counter+1}_{trial_counter+1}, "
                        f"T:{psychopy.core.monotonicClock.getTime():.4f}, Type: {trial_type}",
                el_tracker=el_tracker,
                log_msg=True,
                create_var=False
            )

        num_of_subloops = interim_frames // attention_frames # Num of opportunities for attention-stimuli changes

        # Loop for the number of times the attention stimuli should/can change:
        for interim_subloop in range(num_of_subloops):

            # Set the fixation object's parameters before drawing it ('circle' vs 'letter' depending on condition):
            fixation_obj, n_attention_targets, delay_countdown, is_att_target, att_letter = determine_attention_stimulus(
                condition, trial_counter, acceptable_target_idxs, fixation_obj, norm_colour, att_colour,
                colour_change_chance, target_letter, distractor_letters, n_attention_targets,
                defined_response_delay, delay_countdown, prob_threshold
            )

            # The internal loop spanning the attention period; makes sure only 1 change can occur between subloops:
            for frameN in range(attention_frames):

                # Report an error if the eye-tracker stops recording for some reason if in a practise session:
                if not practice:
                    eyelink_status = el_tracker.isRecording()
                    if eyelink_status != pylink.TRIAL_OK:
                        logger.error(f"Eye-tracker recording has stopped unexpectedly. Code: {eyelink_status}")
                    # else:
                    #     logger.info(f"MSG:   Eye-tracker seems to be recording fine.         Code: {eyelink_status}")

                fixation_obj.draw()

                # Flip the window to proceed through the loop:
                current_flip_time = win.flip()

                # Report the fixation stimulus onset time and type to the eye-tracker if not a practise session:
                if not practice and frameN == 0:
                    msg_eyetracker(
                        msg_identifier="FIXATION_STIM_ONSET",
                        message=f"{session_counter+1}_{block_counter+1}_{trial_counter+1}, "
                                f"T:{current_flip_time:.4f}, Type: {trial_type}, "
                                f"Attention_type: {'Target' if is_att_target else 'Normal'}, "
                                f"Letter: {att_letter if att_letter != '' else 'None'},"
                                f"FrameN: {frameN}",
                        el_tracker=el_tracker,
                        log_msg=True,
                        create_var=False
                    )

                # Get keyboard responses after the flip (The earliest time that participants could respond is after
                # the first flip):
                keys = psychopy.event.getKeys(timeStamped=psychopy.core.monotonicClock)
                if keys:
                    for key_name, key_press_time in keys:
                        if key_name == 'space':
                            keypress_times.append(key_press_time)  # Append the precise timestamp
                            n_attention_responses += 1

                            # Report the keypress to the eye-tracker if not a practise session:
                            if not practice:
                                msg_eyetracker(
                                    msg_identifier="KEY_RESPONSE",
                                    message=f"{session_counter+1}_{block_counter+1}_{trial_counter+1}, "
                                            f"T:{key_press_time:.4f}, Key: {key_name}",
                                    el_tracker=el_tracker,
                                    log_msg=True,
                                    create_var=False
                                )
                        else:
                            # Report other keys pressed:
                            keypress_times.append(key_press_time)
                            if not practice:
                                msg_eyetracker(
                                    msg_identifier="UNEXPECTED_KEY_RESPONSE",
                                    message=f"{session_counter + 1}_{block_counter + 1}_{trial_counter + 1}, "
                                            f"T:{key_press_time:.4f}, Key: {key_name}",
                                    el_tracker=el_tracker,
                                    log_msg=True,
                                    create_var=False
                                )
                        # TODO: Add Esc option that terminates the task safely.

        # Report the start of the interim period to the eye-tracker if it's not a practise session:
        if not practice:
            msg_eyetracker(
                msg_identifier="INTERIM_END",
                message=f"{session_counter+1}_{block_counter+1}_{trial_counter+1}, "
                        f"T:{psychopy.core.monotonicClock.getTime():.4f}, Type: {trial_type}",
                el_tracker=el_tracker,
                log_msg=True,
                create_var=False
            )

    return n_attention_targets, n_attention_responses, delay_countdown