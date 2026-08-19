import numpy as np
from PIL import Image
from scipy.io.wavfile import write
from scipy.ndimage import gaussian_filter1d

# -----------------------------
# Configuration
# -----------------------------
IMAGE = "secret.png"
OUTPUT = "hidden.wav"
SAMPLE_RATE = 44100
DURATION = 10.0
FREQ_MIN = 1000
FREQ_MAX = 18000

# Resolution of the "picture" baked into the spectrogram.
# Higher = finer detail, but more compute + a busier sound.
IMG_WIDTH = 500     # time resolution (horizontal detail)
IMG_HEIGHT = 300     # frequency resolution (vertical detail)

GAMMA = 0.6          # <1 brightens midtones so faint detail is still audible/visible
SMOOTH_MS = 5        # envelope smoothing per row, kills clicking between columns
MIN_BRIGHTNESS = 0.02  # rows/columns fainter than this are treated as silent

# -----------------------------
# Load & prepare image
# -----------------------------
img = Image.open(IMAGE).convert("L")
img = img.resize((IMG_WIDTH, IMG_HEIGHT), Image.LANCZOS)
pixels = np.asarray(img, dtype=np.float64) / 255.0
pixels = np.power(pixels, GAMMA)  # gamma correction for better dynamic range

height, width = pixels.shape

# -----------------------------
# Time & frequency grids
# -----------------------------
samples = int(SAMPLE_RATE * DURATION)
time = np.arange(samples) / SAMPLE_RATE

# Higher rows in the image -> higher pitch (top of image = top of spectrogram)
frequencies = np.linspace(FREQ_MAX, FREQ_MIN, height)

audio = np.zeros(samples, dtype=np.float64)

col_width = samples // width          # samples per image column
smooth_sigma = max(1, int(SAMPLE_RATE * SMOOTH_MS / 1000) / 3)

for y in range(height):
    row = pixels[y]

    if row.max() < MIN_BRIGHTNESS:
        continue  # nothing on this frequency row, skip entirely

    # Turn the row of pixel brightnesses into a full-length amplitude
    # envelope by holding each value for its column's duration.
    envelope = np.repeat(row, col_width)
    if envelope.size < samples:
        envelope = np.pad(envelope, (0, samples - envelope.size), mode="edge")
    elif envelope.size > samples:
        envelope = envelope[:samples]

    # Smooth the steps between columns into ramps -> removes the
    # crackle/click artifacts caused by instantaneous amplitude jumps.
    envelope = gaussian_filter1d(envelope, sigma=smooth_sigma)

    tone = np.sin(2 * np.pi * frequencies[y] * time)
    audio += envelope * tone

# -----------------------------
# Normalize + fade in/out (avoids a hard pop at start/end)
# -----------------------------
peak = np.max(np.abs(audio))
if peak > 0:
    audio /= peak
audio *= 0.85

fade_samples = int(SAMPLE_RATE * 0.02)
fade_in = np.linspace(0, 1, fade_samples)
fade_out = np.linspace(1, 0, fade_samples)
audio[:fade_samples] *= fade_in
audio[-fade_samples:] *= fade_out

# -----------------------------
# Save
# -----------------------------
write(OUTPUT, SAMPLE_RATE, audio.astype(np.float32))
print(f"Created: {OUTPUT}")
