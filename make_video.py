#!/usr/bin/env python3
"""Render demo video: narrated slides from the real demo numbers. Stdlib + PIL + ffmpeg + /opt/hatch/bin/tts."""
import json, os, subprocess, sys
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "video")
os.makedirs(OUT, exist_ok=True)
FB = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FM = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"

SECTIONS = [
    ("OneMemory", "One Memory, Every Coding Agent — ContextCon Theme 01",
     ["The problem: every coding agent starts cold.",
      "Claude Code learns a rule on Monday.",
      "Cursor violates it on Tuesday. Codex never hears it.",
      "Lessons live in local files no other agent can read."],
     "Every coding agent starts every session cold. It re-derives your team's standards, repeats last week's mistakes, and keeps what it learns in a local file that no other agent can read. Claude Code learns a rule on Monday, Cursor violates it on Tuesday, and Codex never hears about it. OneMemory fixes this with one shared memory for every coding agent."),
    ("Teach the standard once", "Codify the project into one Meko datapack",
     ["Architect agent teaches 4 standards, one time:",
      "  STD-NAME   snake_case verb function names",
      "  STD-ERR    never swallow exceptions silently",
      "  STD-SECRET no credentials in code or logs",
      "  STD-TEST   every public function ships a test",
      "One datapack. One MCP endpoint. Every agent."],
     "First, an architect agent teaches the project standards into one Meko datapack, exactly once: naming, error handling, secrets, and tests. The datapack holds conversations, memory, knowledge, decision traces and artifacts, behind a single MCP endpoint that every agent and every tool can reach."),
    ("Code with citations", "Session 1 — coder in Claude Code",
     ["$ python3 onememory.py --demo",
      "Retrieves a relevance-scored slice (not everything)",
      "Writes code, cites the rules it applied:",
      "  cited: STD-NAME, STD-ERR, STD-TEST",
      "Compliance: 3 / 4  — input validation missing"],
     "In session one, a coder working in Claude Code retrieves only the relevant slice of memory, scored for relevance, writes the function, and cites the rule identifiers it applied. Compliance is three out of four. Input validation is missing, because nobody has taught it yet."),
    ("Review, then governed learning", "Session 1 — reviewer in Cursor (fresh session)",
     ["Reviewer finds: LEARN-VALID — missing input validation",
      "Lesson starts as PRIVATE memory",
      "Promotion gate: evidence required, trust bar 0.80",
      "  no evidence -> rejected",
      "  trust 0.50  -> human approval queue",
      "  trust 0.90 + evidence -> promoted as K5"],
     "A reviewer in Cursor, in a completely fresh session, finds the gap. The lesson starts as private memory. To become shared knowledge it must pass a governance gate: evidence is mandatory, and a trust score of zero point eight or higher promotes it automatically. Below the bar, it waits for a human. This lesson had evidence and high trust, so it was promoted as rule K5."),
    ("Learn once, apply everywhere", "Session 2 — brand-new coder in Codex",
     ["Different harness. Zero local memory.",
      "Retrieves the same datapack — now including K5",
      "  cited: STD-NAME, K5, STD-ERR, STD-TEST",
      "Compliance: 4 / 4",
      "What one agent learns, every agent applies."],
     "Now session two: a brand-new coder in Codex. A different tool, with zero local memory. It retrieves the same datapack, which now includes rule K5, and ships fully compliant code, citing the very rule the Cursor reviewer taught the team. What one agent learns, every agent applies."),
    ("Measured, auditable, done", "Results from the recorded demo run",
     ["Compliance:        3/4  ->  4/4 across harnesses",
      "Context tokens:    6,604 -> 171  (-97.4%)",
      "Selftest:          11 / 11 PASS",
      "Every step is a decision trace: ask why, get the trail.",
      "",
      "Teach once. Every agent follows it."],
     "The results are measured, not promised. Compliance rose from three of four to four of four, across different tools. Engineered context cut tokens from six thousand six hundred to one hundred seventy-one, a ninety-seven percent reduction. And every search, promotion and decision is a trace you can audit. Teach the standard once. Every coding agent follows it. That is OneMemory."),
]

def slide(idx, title, subtitle, lines):
    img = Image.new("RGB", (1280, 720), (10, 25, 49))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 1280, 10], fill=(255, 122, 0))
    d.text((60, 48), title, font=ImageFont.truetype(FB, 44), fill=(255, 255, 255))
    d.text((60, 108), subtitle, font=ImageFont.truetype(FR, 24), fill=(255, 170, 80))
    y = 180
    for ln in lines:
        d.text((60, y), ln, font=ImageFont.truetype(FM, 25), fill=(220, 230, 245))
        y += 44
    d.text((60, 668), f"OneMemory — ContextCon Theme 01 · {idx+1}/{len(SECTIONS)}", font=ImageFont.truetype(FR, 18), fill=(140, 160, 190))
    p = os.path.join(OUT, f"slide{idx}.png")
    img.save(p)
    return p

def dur(path):
    r = subprocess.run(["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                       capture_output=True, text=True)
    return float(r.stdout.strip())

def main():
    concat_v, concat_a = [], []
    for i, (title, sub, lines, narr) in enumerate(SECTIONS):
        png = slide(i, title, sub, lines)
        mp3 = os.path.join(OUT, f"narr{i}.mp3")
        if not os.path.exists(mp3):
            r = subprocess.run(["/opt/hatch/bin/tts", "speak", "--output", mp3, "--text-stdin",
                                "--voice", "avocado_v2:MAI_03", "--language", "en"],
                               input=narr, capture_output=True, text=True)
            if r.returncode != 0:
                print("TTS FAIL", i, r.stderr[-300:]); sys.exit(1)
        d = dur(mp3) + 0.4
        concat_v.append(f"file '{png}'\nduration {d:.2f}")
        concat_a.append(f"file '{mp3}'")
        print(f"section {i}: {d:.1f}s")
    last = os.path.join(OUT, f"slide{len(SECTIONS)-1}.png")
    concat_v.append(f"file '{last}'")
    open(os.path.join(OUT, "vlist.txt"), "w").write("\n".join(concat_v) + "\n")
    open(os.path.join(OUT, "alist.txt"), "w").write("\n".join(concat_a) + "\n")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", os.path.join(OUT, "vlist.txt"),
                    "-f", "concat", "-safe", "0", "-i", os.path.join(OUT, "alist.txt"),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest",
                    os.path.join(OUT, "onememory-demo.mp4")], check=True)
    print("VIDEO OK", os.path.join(OUT, "onememory-demo.mp4"), f"{dur(os.path.join(OUT,'onememory-demo.mp4')):.1f}s")

if __name__ == "__main__":
    main()
