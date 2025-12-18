import os
import time
import ctypes
from ctypes import wintypes
import psutil



class OsuBeatmapDetector:
    """Beatmap detector via osu! window title"""

    def __init__(self):
        self.process = None
        self.osu_dir = None
        self.songs_folder = None
        self.current_title = None

    def find_osu_process(self):
        """Find osu! process"""
        for proc in psutil.process_iter(['name', 'pid', 'exe']):
            try:
                if proc.info['name'] and 'osu!' in proc.info['name']:
                    self.process = proc
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return False

    def get_osu_directory(self):
        """Get osu! directory"""
        if self.process:
            try:
                exe_path = self.process.exe()
                self.osu_dir = os.path.dirname(exe_path)
                self.songs_folder = os.path.join(self.osu_dir, "Songs")
                return self.osu_dir
            except:
                return None
        return None

    def get_window_title(self):
        """Get osu! window title"""
        try:
            def get_title(hwnd):
                length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
                buff = ctypes.create_unicode_buffer(length + 1)
                ctypes.windll.user32.GetWindowTextW(hwnd, buff, length + 1)
                return buff.value

            EnumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
            osu_title = None

            def enum_callback(hwnd, lParam):
                nonlocal osu_title
                if ctypes.windll.user32.IsWindowVisible(hwnd):
                    title = get_title(hwnd)
                    if title.startswith("osu!"):
                        osu_title = title
                        return False
                return True

            ctypes.windll.user32.EnumWindows(EnumWindowsProc(enum_callback), 0)
            return osu_title

        except Exception as e:
            return None

    def parse_title(self, title):
        """
        Parse window title
        Format: "osu! - Artist - Title [Difficulty]"
        Returns: (artist, title, difficulty)
        """
        if not title:
            return None, None, None
        if title.startswith("osu! - "):
            content = title[7:]
        elif title.startswith("osu!"):
            content = title[5:].strip()
            if content.startswith("- "):
                content = content[2:]
        else:
            content = title

        difficulty = None
        if '[' in content and ']' in content:
            bracket_start = content.rfind('[')
            bracket_end = content.rfind(']')
            if bracket_start < bracket_end:
                difficulty = content[bracket_start+1:bracket_end].strip()
                content = content[:bracket_start].strip()

        if ' - ' in content:
            parts = content.split(' - ', 1)
            artist = parts[0].strip()
            song_title = parts[1].strip()
            return artist, song_title, difficulty

        return None, None, None

    def find_beatmap_files(self, artist, title, difficulty=None):
        """
        Find all matching .osu files
        Returns list of (path, version, is_exact_match, creator, folder_name)
        """
        if not self.songs_folder or not os.path.exists(self.songs_folder):
            return []

        if not artist or not title:
            return []

        found_files = []

        artist_normalized = artist.lower().strip()
        title_normalized = title.lower().strip()

        for folder_name in os.listdir(self.songs_folder):
            folder_path = os.path.join(self.songs_folder, folder_name)

            if not os.path.isdir(folder_path):
                continue

            for file_name in os.listdir(folder_path):
                if not file_name.endswith('.osu'):
                    continue

                file_path = os.path.join(folder_path, file_name)

                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()

                    file_artist = None
                    file_title = None
                    file_version = None
                    file_creator = None

                    for line in lines[:50]:
                        line = line.strip()
                        if line.startswith("Artist:"):
                            file_artist = line.split(":", 1)[1].strip()
                        elif line.startswith("Title:"):
                            file_title = line.split(":", 1)[1].strip()
                        elif line.startswith("Version:"):
                            file_version = line.split(":", 1)[1].strip()
                        elif line.startswith("Creator:"):
                            file_creator = line.split(":", 1)[1].strip()

                    if file_artist and file_title:
                        artist_match = file_artist.lower().strip() == artist_normalized
                        title_match = file_title.lower().strip() == title_normalized

                        if artist_match and title_match:
                            if difficulty:
                                if file_version and file_version.lower().strip() == difficulty.lower().strip():
                                    found_files.append((file_path, file_version, True, file_creator, folder_name))
                                else:
                                    found_files.append((file_path, file_version, False, file_creator, folder_name))
                            else:
                                found_files.append((file_path, file_version, False, file_creator, folder_name))

                except Exception as e:
                    continue

        found_files.sort(key=lambda x: (not x[2], x[1] or ""))

        return found_files


def read_beatmap_info(filepath):
    """Read information from .osu file"""
    info = {
        'title': '', 'artist': '', 'creator': '', 'version': '',
        'beatmap_id': '', 'hp': '', 'cs': '', 'ar': '', 'od': ''
    }

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()

        for line in lines:
            stripped = line.strip()

            if stripped.startswith("Title:"):
                info['title'] = stripped.split(":", 1)[1].strip()
            elif stripped.startswith("Artist:"):
                info['artist'] = stripped.split(":", 1)[1].strip()
            elif stripped.startswith("Creator:"):
                info['creator'] = stripped.split(":", 1)[1].strip()
            elif stripped.startswith("Version:"):
                info['version'] = stripped.split(":", 1)[1].strip()
            elif stripped.startswith("BeatmapID:"):
                info['beatmap_id'] = stripped.split(":", 1)[1].strip()
            elif stripped.startswith("HPDrainRate:"):
                info['hp'] = stripped.split(":", 1)[1].strip()
            elif stripped.startswith("CircleSize:"):
                info['cs'] = stripped.split(":", 1)[1].strip()
            elif stripped.startswith("ApproachRate:"):
                info['ar'] = stripped.split(":", 1)[1].strip()
            elif stripped.startswith("OverallDifficulty:"):
                info['od'] = stripped.split(":", 1)[1].strip()
    except:
        pass

    return info


def stack_beatmap(input_path, output_path, stack_x=256, stack_y=192, suffix="stacked"):
    """
    Create stacked version of beatmap

    HitObjects format:
    - Circle: x,y,time,type,hitSound,hitSample
    - Slider: x,y,time,type,hitSound,curveType|curvePoints,slides,length,edgeSounds,edgeSets,hitSample
    - Spinner: x,y,time,type,hitSound,endTime,hitSample
    """
    try:
        with open(input_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        result = []
        in_hitobjects = False

        for line in lines:
            stripped = line.strip()

            if stripped.startswith("Version:"):
                original = stripped.split(":", 1)[1].strip()
                line = f"Version:{original} [{suffix}]\n"

            if stripped.startswith("StackLeniency:"):
                line = "StackLeniency:0\n"

            if stripped == "[HitObjects]":
                in_hitobjects = True
                result.append(line)
                continue

            if in_hitobjects:
                if stripped.startswith("["):
                    in_hitobjects = False
                    result.append(line)
                    continue

                if not stripped:
                    result.append(line)
                    continue

                parts = stripped.split(",")

                if len(parts) >= 5:
                    old_x = int(parts[0])
                    old_y = int(parts[1])
                    obj_type = int(parts[3])

                    parts[0] = str(stack_x)
                    parts[1] = str(stack_y)

                    is_slider = (obj_type & 2) != 0

                    if is_slider and len(parts) >= 6:
                        curve_data = parts[5]

                        if '|' in curve_data:
                            curve_parts = curve_data.split('|')
                            curve_type = curve_parts[0]

                            new_curve_points = [curve_type]

                            for i in range(1, len(curve_parts)):
                                point = curve_parts[i]

                                if ':' in point:
                                    point_parts = point.split(':')
                                    if len(point_parts) == 2:
                                        try:
                                            point_x = int(point_parts[0])
                                            point_y = int(point_parts[1])

                                            offset_x = point_x - old_x
                                            offset_y = point_y - old_y

                                            new_point_x = stack_x + offset_x
                                            new_point_y = stack_y + offset_y

                                            new_curve_points.append(f"{new_point_x}:{new_point_y}")
                                        except ValueError:
                                            new_curve_points.append(point)
                                else:
                                    new_curve_points.append(point)

                            parts[5] = '|'.join(new_curve_points)

                    line = ",".join(parts) + "\n"

            result.append(line)

        with open(output_path, "w", encoding="utf-8") as f:
            f.writelines(result)

        return True
    except Exception as e:
        print(f"Processing error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("=" * 70)
    print("        OSU! BEATMAP STACKER - Console Version")
    print("=" * 70)
    print()

    detector = OsuBeatmapDetector()

    # Settings
    stack_x = 256
    stack_y = 192
    suffix = "stacked"

    print("Settings (Enter to change, press Enter to skip):")

    x_input = input(f"Stack X coordinate [{stack_x}]: ").strip()
    if x_input:
        try:
            stack_x = int(x_input)
        except:
            pass

    y_input = input(f"Stack Y coordinate [{stack_y}]: ").strip()
    if y_input:
        try:
            stack_y = int(y_input)
        except:
            pass

    suffix_input = input(f"Difficulty suffix [{suffix}]: ").strip()
    if suffix_input:
        suffix = suffix_input

    print()
    print(f"Settings: X={stack_x}, Y={stack_y}, Suffix='{suffix}'")
    print()
    print("-" * 70)
    print("Searching for osu!...")

    # Find osu! process
    if not detector.find_osu_process():
        print("❌ osu! not found. Launch the game and try again.")
        input("\nPress Enter to exit...")
        return

    osu_dir = detector.get_osu_directory()
    if not osu_dir:
        print("❌ Could not determine osu! directory!")
        input("\nPress Enter to exit...")
        return

    print(f"✅ osu! found: {osu_dir}")
    print(f"📂 Songs folder: {detector.songs_folder}")
    print()
    print("-" * 70)
    print("Monitoring window title...")
    print("💡 Select a beatmap in osu! for auto-detection")
    print("💡 Press Ctrl+C to exit")
    print("-" * 70)
    print()

    last_title = None
    last_processed_file = None

    try:
        while True:
            title = detector.get_window_title()

            if title and title != last_title and title != "osu!":
                last_title = title

                artist, song_title, difficulty = detector.parse_title(title)

                print(f"\n{'=' * 70}")
                print(f"🎵 Beatmap detected from window title:")
                print(f"   Title: {title}")
                print(f"   Artist: {artist if artist else 'not detected'}")
                print(f"   Song: {song_title if song_title else 'not detected'}")
                print(f"   Difficulty: {difficulty if difficulty else 'not specified'}")
                print()

                if artist and song_title:
                    print("🔍 Searching for files...")

                    found_files = detector.find_beatmap_files(artist, song_title, difficulty)

                    if found_files:

                        mappers = {}
                        for fpath, fversion, is_exact, fcreator, ffolder in found_files:
                            if fcreator not in mappers:
                                mappers[fcreator] = []
                            mappers[fcreator].append((fpath, fversion, is_exact, ffolder))

                        print(f"✅ Found {len(found_files)} file(s) from {len(mappers)} mapper(s)")
                        print()

                        selected_mapper = None
                        if len(mappers) > 1:
                            print("📋 Multiple mappers found:")
                            mapper_list = list(mappers.keys())
                            for i, mapper in enumerate(mapper_list, 1):
                                count = len(mappers[mapper])
                                print(f"   {i}. {mapper} ({count} difficulties)")

                            print()
                            choice = input(f"Choose mapper (1-{len(mapper_list)}) or Enter for first: ").strip()

                            if choice.isdigit() and 1 <= int(choice) <= len(mapper_list):
                                selected_mapper = mapper_list[int(choice) - 1]
                            else:
                                selected_mapper = mapper_list[0]
                        else:
                            selected_mapper = list(mappers.keys())[0]

                        print(f"\n✅ Selected mapper: {selected_mapper}")
                        print()

                        mapper_files = mappers[selected_mapper]

                        if len(mapper_files) == 1:
                            beatmap_file = mapper_files[0][0]
                            selected_version = mapper_files[0][1]
                            folder_name = mapper_files[0][3]
                        else:
                            print("📋 Found multiple difficulties:")
                            for i, (fpath, fversion, is_exact, ffolder) in enumerate(mapper_files, 1):
                                marker = "🌟" if is_exact else "  "
                                print(f"   {i}. {marker} [{fversion}]")

                            print()
                            choice = input(f"Choose difficulty (1-{len(mapper_files)}) or Enter for first: ").strip()

                            if choice.isdigit() and 1 <= int(choice) <= len(mapper_files):
                                idx = int(choice) - 1
                            else:
                                idx = 0

                            beatmap_file = mapper_files[idx][0]
                            selected_version = mapper_files[idx][1]
                            folder_name = mapper_files[idx][3]

                        if beatmap_file == last_processed_file:
                            print("\nℹ️  This beatmap was already processed recently")
                            print("-" * 70)
                            print("Waiting for next beatmap...")
                            print("-" * 70)
                            time.sleep(1)
                            continue

                        print(f"\n✅ Selected: [{selected_version}]")
                        print(f"📄 File: {os.path.basename(beatmap_file)}")

                        info = read_beatmap_info(beatmap_file)

                        print(f"\n📋 Beatmap information:")
                        print(f"   Artist: {info['artist']}")
                        print(f"   Title: {info['title']}")
                        print(f"   Difficulty: {info['version']}")
                        print(f"   Mapper: {info['creator']}")
                        if info['beatmap_id']:
                            print(f"   Beatmap ID: {info['beatmap_id']}")
                        print(f"   Settings: HP:{info['hp']} CS:{info['cs']} AR:{info['ar']} OD:{info['od']}")

                        folder = os.path.dirname(beatmap_file)
                        all_diffs = sorted([f for f in os.listdir(folder) if f.endswith('.osu')])

                        print(f"\n⭐ Total difficulties in folder: {len(all_diffs)}")
                        for i, diff in enumerate(all_diffs, 1):
                            marker = "🌟" if diff == os.path.basename(beatmap_file) else "  "
                            try:
                                diff_name = diff.rsplit('[', 1)[1].rsplit(']', 1)[0]
                                print(f"   {i}. {marker} [{diff_name}]")
                            except:
                                print(f"   {i}. {marker} {diff}")

                        print(f"\n💡 Processing options:")
                        print(f"   1. Only selected difficulty [{info['version']}]")
                        print(f"   2. All difficulties ({len(all_diffs)} pcs.)")
                        print(f"   0. Skip")

                        choice = input("\nYour choice (1/2/0): ").strip()

                        if choice == '1':
                            print(f"\n⚙️ Processing selected difficulty...")

                            name_without_ext = os.path.basename(beatmap_file).rsplit(".", 1)[0]
                            if "]" in name_without_ext:
                                parts = name_without_ext.rsplit("]", 1)
                                output_name = f"{parts[0]} - {suffix}].osu"
                            else:
                                output_name = f"{name_without_ext}_{suffix}.osu"

                            output_path = os.path.join(folder, output_name)

                            if stack_beatmap(beatmap_file, output_path, stack_x, stack_y, suffix):
                                print(f"✅ Created: {output_name}")
                                print(f"📁 Folder: {os.path.basename(folder)}")
                                print(f"\n💡 Press F5 in osu! to refresh")
                                last_processed_file = beatmap_file

                        elif choice == '2':
                            print(f"\n⚙️ Processing all difficulties...")
                            processed = 0

                            for diff_file in all_diffs:
                                diff_path = os.path.join(folder, diff_file)

                                name_without_ext = diff_file.rsplit(".", 1)[0]
                                if "]" in name_without_ext:
                                    parts = name_without_ext.rsplit("]", 1)
                                    output_name = f"{parts[0]} - {suffix}].osu"
                                else:
                                    output_name = f"{name_without_ext}_{suffix}.osu"

                                output_path = os.path.join(folder, output_name)

                                if stack_beatmap(diff_path, output_path, stack_x, stack_y, suffix):
                                    processed += 1
                                    try:
                                        diff_name = diff_file.rsplit('[', 1)[1].rsplit(']', 1)[0]
                                        print(f"   ✓ [{diff_name}]")
                                    except:
                                        print(f"   ✓ {diff_file}")

                            print(f"\n✅ Processed difficulties: {processed}")
                            print(f"📁 Folder: {os.path.basename(folder)}")
                            print(f"\n💡 Press F5 in osu! to refresh")
                            last_processed_file = beatmap_file

                        print("\n" + "-" * 70)
                        print("Waiting for next beatmap...")
                        print("-" * 70)

                    else:
                        print("❌ Files not found in Songs folder")
                        print(f"\n💡 Debug info:")
                        print(f"   Searched: Artist='{artist}', Title='{song_title}'")
                        print("\n💡 Try selecting the beatmap again")
                else:
                    print("❌ Could not parse window title")

            time.sleep(1)

    except KeyboardInterrupt:
        print("\n\n" + "=" * 70)
        print("Exiting...")
        print("=" * 70)


if __name__ == "__main__":
    main()
