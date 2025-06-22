import config as config
import psychopy.event
import logging

logger = logging.getLogger(__name__)

def clear_screen(win):
    """
    Clears the PsychoPy window to the calibration background color via a win.flip() call.
    Args:
        win: The PsychoPy window instance.
    """
    win.color = config.BG_COLOUR
    win.flip()


def show_msg(msg_instance, win, text, wait_for_keypress=True, timeout_sec=None):
    """
    Displays a message on the screen using PsychoPy TextStim.
    Uses foreground color from genv for calibration/setup messages.
    Args:
        msg_instance: The PsychoPy TextStim instance to use for displaying the message.
        win: The PsychoPy window instance.
        text (str): The message text to display.
        wait_for_keypress (bool): If True, waits for a keypress or timeout before returning.
        timeout_sec (float or None): If provided and > 0, waits max this many seconds for a keypress.
                                    If None or 0, waits indefinitely (if wait_for_keypress is True).
    """

    # Clear the screen before drawing the message (uses genv color via clear_screen)
    clear_screen(win)
    msg_instance.text = text
    msg_instance.draw()
    win.flip()

    # Wait for keypress if requested or timeout period
    if wait_for_keypress:
        psychopy.event.clearEvents(eventType='keyboard')  # Clear previous presses before waiting
        keys = None
        if timeout_sec is not None and timeout_sec > 0:
            # Wait for the specified duration
            keys = psychopy.event.waitKeys(maxWait=timeout_sec, keyList=None)  # Don't clear within waitKeys
        else:
            # Wait indefinitely
            keys = psychopy.event.waitKeys(keyList=None)

        # Clear the screen AFTER waiting or timeout has finished
        clear_screen(win)

def msg_eyetracker(msg_identifier, message, el_tracker, log_msg=False, create_var=False):
    # Send the message to the eye-tracker:
    el_tracker.sendMessage(f"{msg_identifier} {message}")

    # log the message told to:
    if log_msg:
        logger.info(f"  EL_MSG: {msg_identifier} {message}")

    # Also set it as a var if told to (so it can appear in its own column in the output):
    if create_var:
        el_tracker.sendMessage(f"!V {msg_identifier}_VAR {msg_identifier} {message}")

