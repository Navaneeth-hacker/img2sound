#!/usr/bin/env python3
import os
import sys
import argparse
import glob
import numpy as np
from PIL import Image
from scipy.io.wavfile import write
from scipy.ndimage import gaussian_filter1d

# Define image extensions supported
IMAGE_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.webp')

def convert_image_to_audio(
    image_path,
    output_path,
    duration=10.0,
    sample_rate=44100,
    freq_min=1000,
    freq_max=18000,
    img_width=500,
    img_height=300,
    gamma=0.6,
    smooth_ms=5,
    min_brightness=0.02
):
    """
    Converts a single image file to a spectrogram-encoded WAV audio file.
    """
    print(f"Loading image: {image_path}...")
    img = Image.open(image_path).convert("L")
    img = img.resize((img_width, img_height), Image.LANCZOS)
    pixels = np.asarray(img, dtype=np.float64) / 255.0
    pixels = np.power(pixels, gamma)  # gamma correction
    
    height, width = pixels.shape
    
    # Time & frequency grids
    samples = int(sample_rate * duration)
    time = np.arange(samples) / sample_rate
    
    # Higher rows -> higher pitch
    frequencies = np.linspace(freq_max, freq_min, height)
    
    audio = np.zeros(samples, dtype=np.float64)
    col_width = samples // width
    smooth_sigma = max(1, int(sample_rate * smooth_ms / 1000) / 3)
    
    for y in range(height):
        row = pixels[y]
        if row.max() < min_brightness:
            continue
            
        envelope = np.repeat(row, col_width)
        if envelope.size < samples:
            envelope = np.pad(envelope, (0, samples - envelope.size), mode="edge")
        elif envelope.size > samples:
            envelope = envelope[:samples]
            
        envelope = gaussian_filter1d(envelope, sigma=smooth_sigma)
        tone = np.sin(2 * np.pi * frequencies[y] * time)
        audio += envelope * tone
        
    # Normalize + fade in/out
    peak = np.max(np.abs(audio))
    if peak > 0:
        audio /= peak
    audio *= 0.85
    
    fade_samples = int(sample_rate * 0.02)
    fade_in = np.linspace(0, 1, fade_samples)
    fade_out = np.linspace(1, 0, fade_samples)
    audio[:fade_samples] *= fade_in
    audio[-fade_samples:] *= fade_out
    
    write(output_path, sample_rate, audio.astype(np.float32))
    print(f"Created: {output_path}")

# TUI Helpers
def get_files_and_dirs(path):
    try:
        entries = os.listdir(path)
    except PermissionError:
        return []
        
    dirs = []
    files = []
    
    # check if we can go up
    parent = os.path.dirname(os.path.abspath(path))
    if parent != os.path.abspath(path):
        dirs.append("..")
        
    for entry in entries:
        full_path = os.path.join(path, entry)
        if os.path.isdir(full_path):
            if not entry.startswith('.'):
                dirs.append(entry + "/")
        elif os.path.isfile(full_path) and entry.lower().endswith(IMAGE_EXTENSIONS):
            files.append(entry)
            
    dirs_sorted = sorted([d for d in dirs if d != ".."])
    if ".." in dirs:
        dirs_sorted.insert(0, "..")
    files_sorted = sorted(files)
    
    return dirs_sorted + files_sorted

def run_curses_tui():
    import curses
    
    current_dir = os.getcwd()
    
    def tui_loop(stdscr):
        nonlocal current_dir
        curses.curs_set(0)
        curses.start_color()
        # cyan highlight
        curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_CYAN)
        # yellow for directories
        curses.init_pair(2, curses.COLOR_YELLOW, curses.COLOR_BLACK)
        # green for image files
        curses.init_pair(3, curses.COLOR_GREEN, curses.COLOR_BLACK)

        current_idx = 0
        
        while True:
            items = get_files_and_dirs(current_dir)
            if not items:
                items = [".."]
                
            if current_idx >= len(items):
                current_idx = len(items) - 1
            if current_idx < 0:
                current_idx = 0

            stdscr.clear()
            height, width = stdscr.getmaxyx()

            # Ensure minimal space
            if height < 6 or width < 30:
                stdscr.addstr(0, 0, "Terminal too small!")
                stdscr.refresh()
                key = stdscr.getch()
                if key in (ord('q'), ord('Q'), 27):
                    return None
                continue

            # Header
            stdscr.addstr(0, 0, "=== Spectrogram Sound Converter ===".center(width)[:width-1], curses.A_BOLD)
            path_str = f" Directory: {current_dir} "
            stdscr.addstr(1, 0, path_str.center(width, "-")[:width-1])

            # Draw items
            max_visible = height - 5
            start_idx = max(0, current_idx - max_visible + 1)
            end_idx = min(len(items), start_idx + max_visible)
            if current_idx < start_idx:
                start_idx = current_idx
                end_idx = min(len(items), start_idx + max_visible)

            for i in range(start_idx, end_idx):
                item = items[i]
                is_dir = item.endswith("/") or item == ".."
                
                prefix = "> " if i == current_idx else "  "
                display_text = f"{prefix}{item}"
                display_text = display_text[:width-1]

                y_pos = i - start_idx + 3

                if i == current_idx:
                    stdscr.attron(curses.color_pair(1))
                    stdscr.addstr(y_pos, 0, display_text.ljust(width-1))
                    stdscr.attroff(curses.color_pair(1))
                else:
                    if is_dir:
                        stdscr.attron(curses.color_pair(2))
                        stdscr.addstr(y_pos, 0, display_text)
                        stdscr.attroff(curses.color_pair(2))
                    else:
                        stdscr.attron(curses.color_pair(3))
                        stdscr.addstr(y_pos, 0, display_text)
                        stdscr.attroff(curses.color_pair(3))

            # Footer
            stdscr.addstr(height-2, 0, "-" * (width-1))
            help_str = " [Arrows/WASD]: Move | [Enter]: Select/Open | [Q/ESC]: Quit"
            stdscr.addstr(height-1, 0, help_str[:width-1], curses.A_DIM)

            stdscr.refresh()
            key = stdscr.getch()

            if key in (curses.KEY_UP, ord('k'), ord('w')):
                current_idx = (current_idx - 1) % len(items)
            elif key in (curses.KEY_DOWN, ord('j'), ord('s')):
                current_idx = (current_idx + 1) % len(items)
            elif key in (10, 13, curses.KEY_ENTER):
                selected = items[current_idx]
                if selected == "..":
                    current_dir = os.path.dirname(current_dir)
                    current_idx = 0
                elif selected.endswith("/"):
                    current_dir = os.path.join(current_dir, selected.rstrip("/"))
                    current_idx = 0
                else:
                    return os.path.join(current_dir, selected)
            elif key in (ord('q'), ord('Q'), 27):
                return None

    return curses.wrapper(tui_loop)

def run_fallback_tui():
    """Fallback menu for environments without curses support."""
    current_dir = os.getcwd()
    while True:
        print("\n" + "=" * 45)
        print("=== Spectrogram Sound Converter (Fallback Menu) ===")
        print(f"Current Directory: {current_dir}")
        print("=" * 45)
        
        items = get_files_and_dirs(current_dir)
        if not items:
            items = [".."]
            
        for i, item in enumerate(items):
            print(f"[{i + 1}] {item}")
            
        print("-" * 45)
        print("[Q] Quit / Exit")
        
        choice = input("\nEnter option number or key: ").strip().lower()
        if choice == 'q':
            return None
        
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(items):
                selected = items[idx]
                if selected == "..":
                    current_dir = os.path.dirname(current_dir)
                elif selected.endswith("/"):
                    current_dir = os.path.join(current_dir, selected.rstrip("/"))
                else:
                    return os.path.join(current_dir, selected)
            else:
                print("Invalid number.")
        except ValueError:
            print("Invalid input.")

def main():
    parser = argparse.ArgumentParser(description="Convert an image to a spectrogram-baked audio file.")
    parser.add_argument("-i", "--input", help="Path to the input image file. If omitted, launches TUI selector.")
    parser.add_argument("-o", "--output", help="Path to the output WAV file.")
    parser.add_argument("-d", "--duration", type=float, default=10.0, help="Duration of output audio in seconds.")
    parser.add_argument("--min-freq", type=int, default=1000, help="Minimum frequency of the spectrogram.")
    parser.add_argument("--max-freq", type=int, default=18000, help="Maximum frequency of the spectrogram.")
    
    args = parser.parse_args()
    
    input_path = args.input
    if not input_path:
        # Launch TUI
        try:
            input_path = run_curses_tui()
        except Exception:
            # curses failed or not installed (e.g. Windows without windows-curses)
            input_path = run_fallback_tui()
            
        if not input_path:
            print("Exited.")
            sys.exit(0)
            
    # Determine output path
    output_path = args.output
    if not output_path:
        base, _ = os.path.splitext(os.path.basename(input_path))
        output_path = f"{base}.wav"
        
    try:
        convert_image_to_audio(
            image_path=input_path,
            output_path=output_path,
            duration=args.duration,
            freq_min=args.min_freq,
            freq_max=args.max_freq
        )
    except Exception as e:
        print(f"Error during conversion: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
