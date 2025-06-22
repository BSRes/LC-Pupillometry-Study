import random
import config as config
import logging

logger = logging.getLogger(__name__)

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

        # If the random number is less than chance_of_oddball, then add an oddball and break
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
        logger.info(f"  Added filler block of length {len(final_block)} to fill remaining time.")

    return session_blocks, estimated_duration