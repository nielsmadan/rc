#!/usr/bin/env python3
"""Flatten a WebVTT file into readable text.

Usage: vtt_to_text.py <in.vtt> <out.txt> <plain|ts> <bucket_seconds>

Shared by yt-transcript (YouTube captions) and transcribe (Whisper output),
which both produce VTT. In `ts` mode, cues are merged into buckets of roughly
<bucket_seconds> and each line is prefixed [M:SS], so a caller can locate a
moment in the text and hand that timestamp straight to video-frames.
"""
import re
import sys

CUE = re.compile(r"(\d+:)?(\d\d):(\d\d[.,]\d+)\s+-->")
SKIP = ("WEBVTT", "Kind:", "Language:", "NOTE", "STYLE", "REGION")


def cue_start(line):
    m = CUE.match(line.strip())
    if not m:
        return None
    h = int((m.group(1) or "0:")[:-1])
    return h * 3600 + int(m.group(2)) * 60 + float(m.group(3).replace(",", "."))


def parse(path):
    cues, cur = [], None
    with open(path, encoding="utf-8", errors="replace") as fh:
        for ln in fh:
            ln = ln.rstrip("\n")
            start = cue_start(ln)
            if start is not None:
                cur = start
                continue
            if not ln.strip() or ln.startswith(SKIP) or ln.strip().isdigit():
                continue
            txt = re.sub(r"<[^>]+>", "", ln).strip()
            # YouTube rolling captions repeat the previous line verbatim as the
            # next cue's first line; drop consecutive duplicates.
            if txt and cur is not None and (not cues or cues[-1][1] != txt):
                cues.append((cur, txt))
    return cues


def fmt(sec):
    return f"{int(sec // 60)}:{int(sec % 60):02d}"


def main():
    src, dst, mode, bucket = sys.argv[1], sys.argv[2], sys.argv[3], float(sys.argv[4])
    cues = parse(src)
    if not cues:
        print("ERROR: no cues found in the caption file", file=sys.stderr)
        return 1

    if mode == "ts":
        lines, buf, start = [], [], cues[0][0]
        for t, txt in cues:
            if buf and t - start >= bucket:
                lines.append(f"[{fmt(start)}] " + " ".join(buf))
                buf, start = [], t
            buf.append(txt)
        if buf:
            lines.append(f"[{fmt(start)}] " + " ".join(buf))
        text = "\n".join(lines)
    else:
        text = " ".join(t for _, t in cues)

    with open(dst, "w", encoding="utf-8") as fh:
        fh.write(text + "\n")
    words = len(text.split())
    span = fmt(cues[-1][0])
    print(f"TRANSCRIPT: {dst} ({words} words, {span} long)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
