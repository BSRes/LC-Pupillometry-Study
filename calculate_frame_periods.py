import logging

logger = logging.getLogger(__name__)

def get_nearest_frame(desired_duration_sec, fps):
    """Calculates the number of frames for a duration."""
    if fps <= 0:
        logger.info("Error: FPS must be positive.")
        return 0
    if desired_duration_sec < 0:
        logger.error(f"Warning: Negative duration ({desired_duration_sec}s). Returning 0.")
        return 0
    ideal_frames = desired_duration_sec * float(fps)
    n_frames = int(round(ideal_frames))
    # actual_duration_sec = n_frames / float(fps)
    return n_frames