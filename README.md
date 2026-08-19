# img2sound — hide an image inside an audio spectrogram

Encode a grayscale image directly into the frequency content of a `.wav` file. Play the audio normally and it sounds like an eerie synth drone — but open it in a spectrogram viewer (Audacity, Sonic Visualizer, iZotope RX, etc.) and the picture appears.

This is the same trick behind Aphex Twin's ["Equation" / Windowlicker](https://en.wikipedia.org/wiki/Windowlicker) hidden face and Nine Inch Nails' *Year Zero* spectrogram easter eggs.

## How it works

1. The source image is converted to grayscale and resized to `IMG_WIDTH × IMG_HEIGHT`.
2. Each **row** of the image is mapped to a single sine wave frequency (top row = highest frequency, bottom row = lowest).
3. Each **column** in a row becomes a time slice — the pixel's brightness controls that frequency's volume at that moment.
4. All ~300 sine waves are summed together and smoothed to avoid clicking, producing one mono waveform.
5. When you view the resulting waveform as a spectrogram, brightness-over-time-over-frequency reconstructs the original image.

## Requirements

```bash
pip install numpy scipy pillow
```

## Usage

1. Place a grayscale (or any) image next to the script and name it `secret.png` (or update `IMAGE` below).
2. Run:

```bash
python img2sound.py
```

3. Open the resulting `hidden.wav` in a spectrogram viewer:
   - **Audacity**: import the file, then switch the track's view to *Spectrogram* (click the track name dropdown).
   - **Sonic Visualiser**: open the file, add a *Spectrogram* layer.
   - **macOS**: QuickTime → "Show Movie Inspector" won't show it; use Audacity or `sox hidden.wav -n spectrogram`.




### FFmpeg

```bash
sudo apt install ffmpeg
ffmpeg -i hidden.wav -lavfi showspectrumpic=s=1000x600:legend=0 spectrogram.png
```

`s=WxH` sets output resolution; `legend=0` strips the axis labels for a cleaner image.

### Sonic Visualiser (GUI, but installable via apt)

```bash
sudo apt install sonic-visualiser
sonic-visualiser hidden.wav
```

Then: *Layer → Add Spectrogram → All Channels Mixed*, and export the view as an image via *File → Export Image*.

### Audacity (GUI, via apt or snap)

```bash
sudo apt install audacity
```

Open the file, click the track name dropdown → *Spectrogram*, then use *Export → Export Selected Audio* isn't for images — instead take a screenshot of the track view, or use one of the CLI tools above if you want a clean exported `.png`.

## Reveal it live while it plays (Linux)

The tools above export a static picture. If you want the classic effect — press play and watch the image scroll into view in real time — use one of these instead.

### Baudline (best for this — true real-time scrolling waterfall)

[Baudline](http://www.baudline.com/) is a real-time spectrum analyzer built for exactly this. It plays the audio and draws the spectrogram live as a scrolling waterfall.

```bash
# Ubuntu/Debian: download the .tar.gz from baudline.com (no apt package),
# or grab it via your distro's AUR/community repo if on Arch:
yay -S baudline        # Arch
```

```bash
baudline hidden.wav
```

Open the file, switch to *waterfall* display mode, hit play — the image reveals itself top-to-bottom as the audio plays, no export step needed.

### Friture (Python, cross-platform, real-time)

```bash
pip install friture
friture
```

Load/play the file through your system audio while Friture's spectrogram widget is active; it renders the scrolling waterfall live, same idea as Baudline but easier to `pip install`.

### FFmpeg — render a synced video (no live audio engine needed)

If you just want a video file where the spectrogram scrolls in sync with the audio (shareable, no special player required):

```bash
ffmpeg -i hidden.wav -filter_complex \
  "showspectrum=s=1280x720:mode=combined:color=intensity:scale=log:slide=scroll" \
  -c:v libx264 -pix_fmt yuv420p spectrogram_reveal.mp4
```

Play `spectrogram_reveal.mp4` and the picture scrolls past in time with the audio — effectively "bakes in" the live-reveal effect as a normal video file.

### Sonic Visualiser (GUI, scrolling playhead)

Since it computes the spectrogram up front but then plays the file with a moving playhead over it, it gives a similar "watch it play out" feel without a true live analyzer:

```bash
sudo apt install sonic-visualiser
sonic-visualiser hidden.wav
```

*Layer → Add Spectrogram*, then hit play — the vertical playhead sweeps across the already-rendered spectrogram in time with the audio.

## Configuration

All options are constants at the top of the script:

| Constant | Description |
|---|---|
| `IMAGE` | Path to the source image |
| `OUTPUT` | Path to the generated `.wav` file |
| `SAMPLE_RATE` | Audio sample rate (Hz) |
| `DURATION` | Length of the output audio (seconds) |
| `FREQ_MIN` / `FREQ_MAX` | Frequency range the image is mapped into (Hz) |
| `IMG_WIDTH` | Time resolution — more columns = finer horizontal detail, longer runtime |
| `IMG_HEIGHT` | Frequency resolution — more rows = finer vertical detail, longer runtime |
| `GAMMA` | Gamma correction (<1 brightens midtones so faint detail stays audible) |
| `SMOOTH_MS` | Envelope smoothing per column, prevents clicking artifacts |
| `MIN_BRIGHTNESS` | Rows fainter than this are skipped entirely (speed optimization) |

## Notes & limitations

- Runtime scales roughly with `IMG_HEIGHT × IMG_WIDTH × DURATION` — pushing resolution up significantly will slow things down noticeably.
- Output is mono, 16-bit PCM `.wav` for maximum player/DAW compatibility.
- For the image to read cleanly in a spectrogram viewer, keep `FREQ_MIN`/`FREQ_MAX` within a range your viewer's frequency axis actually displays well (most default views top out around 20 kHz mel/linear scale).
- Very busy/high-detail source images produce dense, noisy-sounding audio — simple high-contrast line art or bold text works best.

## License

MIT — do whatever you want with it.
