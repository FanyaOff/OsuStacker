# osu! Beatmap Stacker

A Python tool that creates stacked versions of osu! beatmaps where all hit objects are placed at a single coordinate position. Console gui writed by llm :D

<img width="1459" height="764" alt="image" src="https://github.com/user-attachments/assets/708329aa-4c90-4c9e-a9fa-33dc42deb706" />


## Usage

1. Launch the executable or script
2. Configure settings (X, Y coordinates and suffix or tap enter to use defaults and stack it in center)
3. Select a beatmap in osu, start playing and exit from the map to detect what map are you playing (yep, i use window name to detect osu betmap)
4. Choose mapper if multiple versions exist
5. Select processing mode (single or all difficulties)
6. Press F5 in osu! to refresh

## Default Settings

- Stack X: 256 (center)
- Stack Y: 192 (center)
- Suffix: "stacked"

## Requirements

- Windows OS
- osu! client running

## Installation

### Compiled Version

1. Download `stacker.exe`
2. Run the executable
3. No Python installation required

### From Source

1. Install Python 3.6+
2. Install dependencies: `pip install psutil`
3. Run: `python stacker.py`
