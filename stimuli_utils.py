
import os
import numpy as np
import math
from PIL import Image
import config # My config file, located in the same dir

def generate_stimulus(
    stim_type,
    pixels_per_degree, # This MUST be provided when calling the function
    output_dir=config.STIM_DIR,
    filename=None,
    size_deg=config.DEFAULT_SIZE_DEG,
    background_lum=config.DEFAULT_BACKGROUND_LUM,
    gabor_freq_cpd=None, # Specify for Gabors if not using 'coarse'/'fine' types
    gabor_contrast=config.DEFAULT_GABOR_CONTRAST,
    gabor_sigma_factor=config.DEFAULT_GABOR_SIGMA_DEG_FACTOR
):
    """
    Generates a Gabor patch or a random-dot noise disk stimulus and saves it.

    Args:
        stim_type (str): Type of stimulus. Options:
                         'gabor_coarse', 'gabor_fine', 'noise_disk'.
        pixels_per_degree (float): Screen resolution in pixels per degree.
                                   CRITICAL for correct stimulus scaling. MUST be provided.
        output_dir (str): Directory to save the stimulus image. Defaults to config.STIM_DIR.
        filename (str, optional): Base filename (without extension).
                                   If None, a default name is generated.
        size_deg (float): Size of the stimulus (diameter/width) in degrees. Defaults to config.DEFAULT_SIZE_DEG.
        background_lum (float): Background luminance (0.0 to 1.0). Stimulus
                                mean luminance will match this. Defaults to config.DEFAULT_BACKGROUND_LUM.
        gabor_freq_cpd (float, optional): Spatial frequency in cycles per degree
                                          for Gabor patches. Overrides defaults
                                          if stim_type is 'gabor_coarse'/'fine'.
        gabor_contrast (float): Michelson contrast for the Gabor patch (0.0 to 1.0). Defaults to config.DEFAULT_GABOR_CONTRAST.
        gabor_sigma_factor (float): Standard deviation of the Gaussian envelope
                                    for Gabor/Noise Disk, expressed as
                                    size_deg / gabor_sigma_factor. Defaults to config.DEFAULT_GABOR_SIGMA_DEG_FACTOR.

    Returns:
        str: The full path to the saved image file.
    """
    # --- Input Validation and Setup ---
    if pixels_per_degree is None or pixels_per_degree <= 0:
        raise ValueError("pixels_per_degree must be a positive value and provided to generate_stimulus.")

    allowed_types = ['gabor_coarse', 'gabor_fine', 'noise_disk']
    if stim_type not in allowed_types:
        raise ValueError(f"stim_type must be one of: {allowed_types}")

    # Determine frequency and type name based on stim_type and config defaults
    if stim_type == 'gabor_coarse':
        freq_cpd = config.FREQ_COARSE_CPD if gabor_freq_cpd is None else gabor_freq_cpd
        gabor_type_name = "coarse"
        default_filename = config.COARSE_GABOR_FILENAME # Use filename from config if not overridden
    elif stim_type == 'gabor_fine':
        freq_cpd = config.FREQ_FINE_CPD if gabor_freq_cpd is None else gabor_freq_cpd
        gabor_type_name = "fine"
        default_filename = config.FINE_GABOR_FILENAME # Use filename from config if not overridden
    elif 'gabor' in stim_type and gabor_freq_cpd is not None:
        # Case for specifying frequency directly (though current setup doesn't use it)
        freq_cpd = gabor_freq_cpd
        gabor_type_name = f"{freq_cpd:.1f}cpd"
        default_filename = f"gabor_{gabor_type_name}_{size_deg:.1f}deg_{freq_cpd:.1f}cpd" # Generic default
    elif stim_type == 'noise_disk':
        default_filename = config.NOISE_DISK_FILENAME # Use filename from config if not overridden
        pass # No frequency needed
    else:
        raise ValueError("Invalid configuration for stim_type and gabor_freq_cpd.")

    # Use provided filename or the default based on type
    if filename is None:
        filename = default_filename

    # Calculate size in pixels (ensure it's an odd number for perfect centering)
    size_pix = int(round(size_deg * pixels_per_degree))
    if size_pix % 2 == 0:
        size_pix += 1

    # Create coordinate grid (centered at 0, units in degrees)
    axis_pix = np.arange(size_pix) - size_pix // 2
    x_pix, y_pix = np.meshgrid(axis_pix, axis_pix)
    x_deg = x_pix / pixels_per_degree
    y_deg = y_pix / pixels_per_degree

    # Calculate Gaussian envelope standard deviation in degrees using config default factor
    sigma_deg = size_deg / gabor_sigma_factor
    if sigma_deg <= 0:
         raise ValueError("gabor_sigma_factor must result in a positive sigma_deg.")

    # --- Generate Stimulus Array (0.0 to 1.0 range) ---
    stim_array = None

    if 'gabor' in stim_type:
        # 1. Calculate Sine Wave Grating
        omega = 2 * np.pi * freq_cpd
        grating = np.sin(omega * x_deg)

        # 2. Calculate Gaussian Envelope
        exponent = -(x_deg**2 + y_deg**2) / (2 * sigma_deg**2)
        envelope = np.exp(np.maximum(exponent, -700)) # Clamp large negative exponents

        # 3. Combine grating and envelope, scale by contrast, add background
        stim_array = background_lum + gabor_contrast * 0.5 * grating * envelope

    elif stim_type == 'noise_disk':
        # 1. Generate binary random dot pattern centered around background lum
        dot_low = max(0.0, background_lum - 0.5)
        dot_high = min(1.0, background_lum + 0.5)
        noise_pattern = np.random.choice([dot_low, dot_high], size=(size_pix, size_pix))

        # 2. Calculate Gaussian Envelope (same as Gabor)
        exponent = -(x_deg**2 + y_deg**2) / (2 * sigma_deg**2)
        envelope = np.exp(np.maximum(exponent, -700))

        # 3. Combine noise and envelope
        stim_array = noise_pattern * envelope + background_lum * (1 - envelope)

    # --- Clip, Convert to Image Format, and Save ---
    stim_array = np.clip(stim_array, 0.0, 1.0)
    img_array = (stim_array * 255).astype(np.uint8)
    img = Image.fromarray(img_array, mode='L') # 'L' mode is for grayscale

    # Ensure output directory exists (using path from config)
    os.makedirs(output_dir, exist_ok=True)

    # Construct full file path and save
    filepath = os.path.join(output_dir, f"{filename}.png") # Save as PNG
    img.save(filepath)
    print(f"Saved stimulus to: {filepath}")

    return filepath