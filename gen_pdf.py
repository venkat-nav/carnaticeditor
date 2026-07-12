#!/usr/bin/env python3
"""Regenerate composition PDFs from .txt notation files using fpdf2 + Georgia."""
import re, os
from fpdf import FPDF

TALAS = {
    "adi":          {"label": "Adi (4+2+2)",       "angas": [4, 2, 2]},
    "rupaka":       {"label": "Rupaka (2+4)",       "angas": [2, 4]},
    "misrachapu":   {"label": "Misra Chapu (3+4)",  "angas": [3, 4]},
    "khandachapu":  {"label": "Khanda Chapu (2+3)", "angas": [2, 3]},
    "triputa":      {"label": "Triputa (3+2+2)",    "angas": [3, 2, 2]},
    "jhampa":       {"label": "Jhampa (7+1+2)",     "angas": [7, 1, 2]},
    "ata":          {"label": "Ata (5+5+2+2)",      "angas": [5, 5, 2, 2]},
}
SCALES = {
    "mohanam": "Mohanam", "shankarabharanam": "Shankarabharanam",
    "kalyani": "Kalyani", "harikambhoji": "Harikambhoji",
    "kambhoji": "Kambhoji", "kharaharapriya": "Kharaharapriya",
    "natabhairavi": "Natabhairavi", "todi": "Todi",
    "charukeshi": "Charukeshi", "mayamalavagowla": "Mayamalavagowla",
}

GEORGIA      = "/System/Library/Fonts/Supplemental/Georgia.ttf"
GEORGIA_BOLD = "/System/Library/Fonts/Supplemental/Georgia Bold.ttf"


def parse_beat_string(s):
    """Return list of (text, underline, octave) triples for one beat token string.
    octave: 1=upper, -1=lower, 0=middle; None for carry/extension tokens."""
    if s in ("....", "----", ""):
        return []
    parts = []
    in_dbl = False
    # collect consecutive tokens before flushing a group
    group_text, group_oct = "", []

    def flush():
        nonlocal group_text, group_oct
        if group_text:
            # For a group: use first token's octave (common case), None means mixed
            oct = group_oct[0] if group_oct else 0
            parts.append((group_text, in_dbl, oct))
            group_text = ""; group_oct = []

    i = 0
    while i < len(s):
        ch = s[i]
        if ch == "[":   flush(); in_dbl = True;  i += 1; continue
        if ch == "]":   flush(); in_dbl = False; i += 1; continue
        if ch in ("^", "_"):
            oct = 1 if ch == "^" else -1
            i += 1
            if i < len(s) and s[i].isalpha():
                let = s[i]; i += 1
                if i < len(s) and s[i] in "123": i += 1
                ext = ""
                while i < len(s) and s[i] in (",", ";"): ext += s[i]; i += 1
                if not in_dbl: flush()
                group_text += let + ext; group_oct.append(oct)
                if not in_dbl: flush()
        elif ch.isalpha():
            let = ch; i += 1
            if i < len(s) and s[i] in "123": i += 1
            ext = ""
            while i < len(s) and s[i] in (",", ";"): ext += s[i]; i += 1
            if not in_dbl: flush()
            group_text += let + ext; group_oct.append(0)
            if not in_dbl: flush()
        elif ch in (",", ";"):
            group_text += ch; i += 1
        else:
            i += 1
    flush()
    return parts


def parse_txt(path):
    with open(path, encoding="utf-8") as f:
        lines = [l.strip() for l in f if l.strip()]
    tala_key, scale_key = "adi", "mohanam"
    avartanams = []
    pending_annotation = ""
    for line in lines:
        if line.startswith("TALA:"):    tala_key  = line[5:].strip(); continue
        if line.startswith("SCALE:"):   scale_key = line[6:].strip(); continue
        if line.startswith("TEMPO:"):   continue
        if line.startswith("SECTION:"): pending_annotation = line[8:].strip(); continue
        m = re.match(r"Avartanam\s+\d+:\s*\|\|(.*)\|\|", line)
        if not m: continue
        beats = []
        for part in m.group(1).strip().split("|"):
            beats.extend(part.strip().split())
        avartanams.append({"annotation": pending_annotation, "beats": beats})
        pending_annotation = ""
    return tala_key, scale_key, avartanams


def make_pdf(txt_path, pdf_path):
    tala_key, scale_key, avartanams = parse_txt(txt_path)
    tala        = TALAS.get(tala_key, TALAS["adi"])
    scale_label = SCALES.get(scale_key, scale_key.title())
    anga_beats  = tala["angas"]
    total_beats = sum(anga_beats)

    pdf = FPDF(unit="mm", format="A4")
    pdf.add_font("Geo",  "",  GEORGIA)
    pdf.add_font("GeoB", "",  GEORGIA_BOLD)
    pdf.set_auto_page_break(False)
    pdf.add_page()

    PW, PH, ML, MR = 210, 297, 15, 15
    usable = PW - ML - MR

    RED  = (153, 60, 29)
    DARK = (26, 26, 26)
    GREY = (136, 135, 128)

    # ── header ───────────────────────────────────────────────────────────────
    pdf.set_font("GeoB", "", 18)
    pdf.set_text_color(*DARK)
    pdf.set_xy(ML, 18); pdf.cell(0, 8, "Jatiswaram notation")

    pdf.set_font("Geo", "", 10)
    pdf.set_text_color(*RED)
    pdf.set_xy(ML, 27)
    pdf.cell(0, 6, f"Tala: {tala['label']}   ·   Raga: {scale_label}")

    pdf.set_draw_color(*RED)
    pdf.set_line_width(0.5)
    pdf.line(ML, 35, PW - MR, 35)

    # ── measure widths ────────────────────────────────────────────────────────
    NOTE_SZ = 12
    pdf.set_font("GeoB", "", NOTE_SZ)
    dbl_bar_w = pdf.get_string_width("||") + 2       # "||" stands for ‖
    bar_w     = pdf.get_string_width("|")  + 2
    total_bar_w = 2 * dbl_bar_w + (len(anga_beats) - 1) * bar_w
    beat_w = (usable - total_bar_w) / total_beats

    LINE_H = 10
    y = 44

    for av in avartanams:
        annotation  = av["annotation"] if isinstance(av, dict) else ""
        beat_strings = av["beats"]    if isinstance(av, dict) else av

        if annotation:
            if y + 14 > PH - 16:
                pdf.add_page(); y = 20
            pdf.set_font("GeoB", "", 11)
            pdf.set_text_color(*DARK)
            pdf.set_xy(ML, y); pdf.cell(0, 6, annotation)
            y += 6
            pdf.set_draw_color(*RED)
            pdf.set_line_width(0.4)
            pdf.line(ML, y, PW - MR, y)
            y += 5

        if y + LINE_H > PH - 16:
            pdf.add_page(); y = 20

        x = ML

        # opening ||
        pdf.set_font("GeoB", "", NOTE_SZ)
        pdf.set_text_color(*RED)
        pdf.set_xy(x, y - 4); pdf.cell(dbl_bar_w, 6, "||")
        x += dbl_bar_w

        beat_idx = 0
        for ai, nb in enumerate(anga_beats):
            for _ in range(nb):
                bs = beat_strings[beat_idx] if beat_idx < len(beat_strings) else ""
                beat_idx += 1
                parts = parse_beat_string(bs)
                if not parts:
                    x += beat_w; continue

                def note_font(oct): return "GeoB" if oct == 1 else "Geo"
                total_w = 0
                for text, underline, octave in parts:
                    pdf.set_font(note_font(octave), "", NOTE_SZ)
                    total_w += pdf.get_string_width(text)
                cx = x + (beat_w - total_w) / 2

                for text, underline, octave in parts:
                    pdf.set_font(note_font(octave), "", NOTE_SZ)
                    tw = pdf.get_string_width(text)
                    pdf.set_text_color(*DARK)
                    pdf.set_xy(cx, y - 4); pdf.cell(tw, 6, text)
                    if underline:
                        pdf.set_draw_color(*DARK)
                        pdf.set_line_width(0.3)
                        pdf.line(cx, y + 1.5, cx + tw, y + 1.5)
                    if octave == 1:
                        pdf.set_font("GeoB", "", 9)
                        pdf.set_xy(cx + tw / 2 - 1.2, y - 8.5); pdf.cell(2.4, 3, "·")
                        pdf.set_font("GeoB", "", NOTE_SZ)
                    elif octave == -1:
                        pdf.set_font("Geo", "", 9)
                        pdf.set_xy(cx + tw / 2 - 1.2, y + 1.5); pdf.cell(2.4, 3, "·")
                        pdf.set_font("Geo", "", NOTE_SZ)
                    cx += tw

                x += beat_w

            if ai < len(anga_beats) - 1:
                pdf.set_font("GeoB", "", NOTE_SZ)
                pdf.set_text_color(*RED)
                pdf.set_xy(x, y - 4); pdf.cell(bar_w, 6, "|")
                x += bar_w

        # closing ||
        pdf.set_font("GeoB", "", NOTE_SZ)
        pdf.set_text_color(*RED)
        pdf.set_xy(x, y - 4); pdf.cell(dbl_bar_w, 6, "||")

        y += LINE_H

    # ── footer ────────────────────────────────────────────────────────────────
    pdf.set_font("Geo", "", 7)
    pdf.set_text_color(*GREY)
    pdf.set_xy(ML, PH - 10)
    pdf.cell(0, 5, "Dot above = upper octave · Dot below = lower octave · "
                   "Underline = double speed (2×) · | divides angas · || marks samam")

    pdf.output(pdf_path)
    print(f"Written: {pdf_path}")


if __name__ == "__main__":
    base = os.path.join(os.path.dirname(os.path.abspath(__file__)), "compositions")
    make_pdf(
        os.path.join(base, "Kambhoji Jatiswara.txt"),
        os.path.join(base, "Kambhoji Jataswara.pdf"),
    )
    make_pdf(
        os.path.join(base, "MohanaJatiswara.txt"),
        os.path.join(base, "Mohana Jatiswara.pdf"),
    )
