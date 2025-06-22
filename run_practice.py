import plan_blocks_and_sessions
import block_handler
from basic_helpers import show_msg
from math import floor, ceil
import logging

logger = logging.getLogger(__name__)

def run_practice(
        practice_condition, max_duration, attention_duration, interim_duration, min_standards, oddball_odds,
        norm_colour, att_colour, rare_odd_threshold, win, standard_stimulus_obj, main_oddball_obj, rare_oddball_obj,
        standard_stimulus_name, main_oddball_name, rare_oddball_name, fixation_obj, attention_frames, main_stim_frames,
        interim_frames, colour_change_chance, target_letter, distractor_letters, accepted_response_accuracy,
        reusable_message_obj, defined_response_delay, delay_countdown, prob_threshold, session_counter,
        experiment_run_number, el_tracker
):
    # Define a bool that is False by default and changes to True if participants achieve the desired accuracy. This
    # gets returned, thereby dictating whether the practice session must be repeated.
    practice_complete = False

    if experiment_run_number <= 1:

        # Get a set of practice blocks to work with:
        s_blocks, est_dur = plan_blocks_and_sessions.populate_session(
            max_session_time_min=max_duration,
            attention_duration_sec=attention_duration,
            interim_duration_sec=interim_duration,
            min_standards=min_standards,
            chance_of_oddball=oddball_odds
        )
        logger.info(f"  Practice Blocks={len(s_blocks)}, Est. Runtime={int(est_dur / 60)}:{round(est_dur % 60,2):05.2f}")

        # Set and show the instructions for the session's condition:
        instr_text = f"Practice Round.\n\n"
        if practice_condition == 'attend':
            instr_text += "You will see circular patterns appear behind a small grey circle.\n"
            instr_text += "Press the SPACEBAR ONLY when the small grey circle changes colour.\n"
            instr_text += "Keep your eyes on the small gray circle.\n\n"
        elif practice_condition == 'divert':
            instr_text += "You will see circular patterns appear behind a stream of changing letters.\n"
            instr_text += "Press the SPACEBAR as quickly as possible ONLY on the THIRD 'X' in a row.\n"
            instr_text += "Ignore the circular patterns and focus on the letters.\n\n"
        instr_text += f"Press any key to start."

        show_msg(reusable_message_obj, win, instr_text, wait_for_keypress=True)

        # Run the blocks, but with the practice param set thereby reducing logging.
        # The chance of colour changes in the 'attend' condition is also increased, and the number of targets and key
        # presses are returned:

        n_responses = 0
        n_targets = 0
        for block_counter, block in enumerate(s_blocks):
            num_of_targets, num_of_keypresses, delay_countdown = block_handler.run_block(
                block=block,
                condition=practice_condition,
                norm_colour=norm_colour,
                att_colour=att_colour,
                rare_odd_threshold=rare_odd_threshold,
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
                colour_change_chance=colour_change_chance,
                target_letter=target_letter,
                distractor_letters=distractor_letters,
                defined_response_delay=defined_response_delay,
                delay_countdown=delay_countdown,
                prob_threshold=prob_threshold,
                session_counter=session_counter,
                block_counter=block_counter,
                el_tracker=el_tracker,
                practice=True
            )
            # Keep track of the total number of responses and targets recorded over the blocks for this practice session:
            n_responses += num_of_keypresses
            n_targets += num_of_targets

        # Figure out how many times the participant should have responded:
        if practice_condition == "attend":
            expected_responses = n_targets
        elif practice_condition == "divert":
            expected_responses = n_targets // 3

        # Calculate the upper and lowerbounds for the acceptable number of responses:
        lower_bound = floor(expected_responses * accepted_response_accuracy)
        upper_bound = ceil(expected_responses * (2 - accepted_response_accuracy))

        # log some debugging info:
        logger.info(f"\nNumber of expected responses: {expected_responses:.2f}"
              f"\nNumber of given responses:    {n_responses:.2f}"
              f"\nLower bound:                  {lower_bound:.2f}"
              f"\nUpper bound:                  {upper_bound:.2f} \n")

        if lower_bound <= n_responses <= upper_bound:
            logger.info(
                f"The number of responses ({n_responses}) is within the acceptable range "
                f"({lower_bound:.2f} - {upper_bound:.2f}).")
            practice_complete = True
        else:
            logger.info(
                f"The number of responses ({n_responses}) is outside the acceptable range "
                f"({lower_bound:.2f} - {upper_bound:.2f}).")
            practice_complete = False

    else:

        # Set and show the instructions for the session's condition:
        instr_text = f"Instructions .\n\n"
        if practice_condition == 'attend':
            instr_text += "You will see circular patterns appear behind a small grey circle.\n"
            instr_text += "Press the SPACEBAR ONLY when the small grey circle changes colour.\n"
            instr_text += "Keep your eyes on the small gray circle.\n\n"
        elif practice_condition == 'divert':
            instr_text += "You will see circular patterns appear behind a stream of changing letters.\n"
            instr_text += "Press the SPACEBAR as quickly as possible ONLY on the THIRD 'X' in a row.\n"
            instr_text += "Ignore the circular patterns and focus on the letters.\n\n"
        instr_text += f"Press any key to start."

        show_msg(reusable_message_obj, win, instr_text, wait_for_keypress=True)

        practice_complete = True

    return practice_complete
