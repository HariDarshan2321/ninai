#!/usr/bin/env python3
"""Render actual product captures into narrated video, captions and chapters."""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile
import textwrap

ROOT = Path(__file__).resolve().parents[1]


def run(*args):
    subprocess.run(args, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def stamp(seconds):
    m = round(seconds * 1000)
    return f"{m // 3600000:02}:{m // 60000 % 60:02}:{m // 1000 % 60:02}.{m % 1000:03}"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture", type=Path)
    parser.add_argument("--voice", default="Samantha")
    args = parser.parse_args()
    source = args.capture.resolve()
    data = json.loads(source.read_text())
    frames, chapters = data["frames"], data["chapters"]
    if not frames or not chapters:
        raise SystemExit("Record actual UI interactions first.")
    offsets, total = [], 0.0
    for f in frames:
        path = (source.parent / f["file"]).resolve()
        if path.parent != source.parent or not path.is_file() or float(f["duration"]) <= 0:
            raise SystemExit("Invalid real capture frame.")
        offsets.append(total)
        total += float(f["duration"])
    assets = ROOT / "website/public/assets"
    output, subtitles, timeline = [], ["WEBVTT", ""], 0.0
    with tempfile.TemporaryDirectory(prefix="ninai-walkthrough-") as directory:
        work, segments = Path(directory), []
        for n, chapter in enumerate(chapters):
            start, end = float(chapter["start"]), float(chapter["end"])
            selected = [i for i, t in enumerate(offsets) if start <= t < end]
            if not selected:
                raise SystemExit("Chapter has no captured UI frames.")
            audio = work / f"voice{n}.aiff"
            narration = str(chapter["instruction"])
            run("say", "-v", args.voice, "-r", "175", "-o", str(audio), narration)
            length = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(audio)], text=True).strip())
            target = max(end - start, length + .7)
            scale, entries = target / (end - start), []
            for i in selected:
                path = str((source.parent / frames[i]["file"]).resolve()).replace("'", "'\\''")
                entries.extend((f"file '{path}'", f"duration {float(frames[i]['duration']) * scale:.6f}"))
            entries.append(entries[-2])
            listing = work / f"frames{n}.txt"
            listing.write_text("\n".join(entries) + "\n")
            segment = work / f"segment{n}.mp4"
            run("ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(listing), "-i", str(audio),
                "-vf", "scale=1280:900:force_original_aspect_ratio=decrease,pad=1280:900:(ow-iw)/2:(oh-ih)/2:color=0x0b302b,setsar=1",
                "-af", "apad", "-t", f"{target:.3f}", "-r", "24", "-c:v", "libx264", "-preset", "fast", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", str(segment))
            segments.append(segment)
            output.append({**chapter, "start": round(timeline, 3), "end": round(timeline + target, 3)})
            subtitles.extend((str(n + 1), f"{stamp(timeline)} --> {stamp(timeline + target)}", textwrap.fill(narration, 70), ""))
            timeline += target
        listing = work / "segments.txt"
        listing.write_text("\n".join(f"file '{p}'" for p in segments) + "\n")
        run("ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(listing), "-c", "copy", "-movflags", "+faststart", str(assets / "ninai-install-guide.mp4"))
        run("ffmpeg", "-y", "-ss", "1", "-i", str(assets / "ninai-install-guide.mp4"), "-frames:v", "1", "-q:v", "2", str(assets / "ninai-install-poster.jpg"))
    (assets / "ninai-install-guide.vtt").write_text("\n".join(subtitles).rstrip() + "\n")
    (assets / "ninai-install-chapters.json").write_text(json.dumps({"title": "Your first private handoff", "duration": round(timeline, 3),
        "recording": "Actual local product UI with synthetic sample data. Model calls occur between scenes; waiting is edited. Narration uses a system voice.", "chapters": output}, indent=2) + "\n")
    print(f"Rendered {len(chapters)} actual UI chapters, {timeline:.1f} seconds.")


if __name__ == "__main__":
    main()
