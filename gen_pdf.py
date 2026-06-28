#!/usr/bin/env python3
"""Regenerate composition PDFs from .txt notation files using fpdf2."""
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

FONT_PATH = "/System/Library/Fonts/Palatino.ttc"


def parse_beat_string(s):
    """Return list of (text_str, underline) pairs for one beat string."""
    if s in ("....", "----", ""):
        return []
    parts = []
    i = 0
    in_dbl = False
    group = ""

    def flush():
        nonlocal group
        if group:
            parts.append((group, in_dbl))
            group = ""

    while i < len(s):
        ch = s[i]
        if ch == "[":
            flush(); in_dbl = True; i += 1; continue
        if ch == "]":
            flush(); in_dbl = False; i += 1; continue
        if ch in ("^", "_"):
            oct_mark = "̇" if ch == "^" else "̣"
            i += 1
            if i < len(s) and s[i].isalpha():
                let = s[i]; i += 1
                if i < len(s) and s[i] in "123":
                    i += 1  # skip variant digit
                ext = ""
                while i < len(s) and s[i] in (",", ";"):
                    ext += s[i]; i += 1
                group += let + oct_mark + ext
        elif ch.isalpha():
            let = ch; i += 1
            if i < len(s) and s[i] in "123":
                i += 1
            ext = ""
            while i < len(s) and s[i] in (",", ";"):
                ext += s[i]; i += 1
            group += let + ext
        elif ch in (",", ";"):
            group += ch; i += 1
        else:
            i += 1
    flush()
    return parts


def parse_txt(path):
    with open(path, encoding="utf-8") as f:
        raw = [l.strip() for l in f if l.strip()]
    tala_key, scale_key = "adi", "mohanam"
    avartanams = []
    for line in raw:
        if line.startswith("TALA:"): tala_key = line[5:].strip(); continue
        if line.startswith("SCALE:"): scale_key = line[6:].strip(); continue
        if line.startswith("TEMPO:"): continue
        m = re.match(r"Avartanam\s+\d+:\s*\|\|(.*)\|\|", line)
        if not m: continue
        body = m.group(1).strip()
        beats = []
        for part in body.split("|"):
            beats.extend(part.strip().split())
        avartanams.append(beats)
    return tala_key, scale_key, avartanams


def make_pdf(txt_path, pdf_path):
    tala_key, scale_key, avartanams = parse_txt(txt_path)
    tala = TALAS.get(tala_key, TALAS["adi"])
    scale_label = SCALES.get(scale_key, scale_key.title())
    anga_beats = tala["angas"]
    total_beats = sum(anga_beats)

    pdf = FPDF(unit="mm", format="A4")
    pdf.add_font("Pal",  "",  FONT_PATH)
    pdf.add_font("Pal",  "B", FONT_PATH)
    pdf.set_auto_page_break(False)
    pdf.add_page()

    PW, PH, ML, MR = 210, 297, 15, 15
    usable = PW - ML - MR

    # Title
    pdf.set_font("Pal", "B", 18)
    pdf.set_text_color(26, 26, 26)
    pdf.set_xy(ML, 18)
    pdf.cell(0, 8, "Jatiswaram notation")

    # Subtitle
    pdf.set_font("Pal", "", 10)
    pdf.set_text_color(153, 60, 29)
    pdf.set_xy(ML, 27)
    pdf.cell(0, 6, f"Tala: {tala['label']}   ·   Raga: {scale_label}")
    pdf.set_text_color(26, 26, 26)

    # Rule
    pdf.set_draw_color(153, 60, 29)
    pdf.set_line_width(0.5)
    pdf.line(ML, 35, PW - MR, 35)
    pdf.set_draw_color(0)

    # Measure column widths using the note font
    pdf.set_font("Pal", "B", 13)
    dbl_bar_w = pdf.get_string_width("‖") + 2
    bar_w     = pdf.get_string_width("|") + 2
    total_bar_w = 2 * dbl_bar_w + (len(anga_beats) - 1) * bar_w
    beat_w = (usable - total_bar_w) / total_beats

    LINE_H = 11
    y = 44

    for beat_strings in avartanams:
        if y + LINE_H > PH - 18:
            pdf.add_page()
            y = 20

        x = ML

        # Opening ‖
        pdf.set_font("Pal", "B", 13)
        pdf.set_text_color(153, 60, 29)
        pdf.set_xy(x, y - 4.5)
        pdf.cell(dbl_bar_w, 6, "‖")
        x += dbl_bar_w

        beat_idx = 0
        for ai, nb in enumerate(anga_beats):
            for _ in range(nb):
                bs = beat_strings[beat_idx] if beat_idx < len(beat_strings) else ""
                beat_idx += 1
                parts = parse_beat_string(bs)

                if parts:
                    pdf.set_font("Pal", "", 13)
                    total_w = sum(pdf.get_string_width(t) for t, _ in parts)
                    cx = x + (beat_w - total_w) / 2

                    for text, underline in parts:
                        pdf.set_font("Pal", "", 13)
                        pdf.set_text_color(26, 26, 26)
                        tw = pdf.get_string_width(text)
                        pdf.set_xy(cx, y - 4.5)
                        pdf.cell(tw, 6, text)
                        if underline:
                            pdf.set_draw_color(26, 26, 26)
                            pdf.set_line_width(0.25)
                            pdf.line(cx, y + 1.0, cx + tw, y + 1.0)
                            pdf.set_draw_color(0)
                        cx += tw

                x += beat_w

            # Anga separator
            if ai < len(anga_beats) - 1:
                pdf.set_font("Pal", "B", 13)
                pdf.set_text_color(153, 60, 29)
                pdf.set_xy(x, y - 4.5)
                pdf.cell(bar_w, 6, "|")
                x += bar_w

        # Closing ‖
        pdf.set_font("Pal", "B", 13)
        pdf.set_text_color(153, 60, 29)
        pdf.set_xy(x, y - 4.5)
        pdf.cell(dbl_bar_w, 6, "‖")
        pdf.set_text_color(0)

        y += LINE_H

    # Footer
    pdf.set_font("Pal", "", 8)
    pdf.set_text_color(136, 135, 128)
    pdf.set_xy(ML, PH - 12)
    pdf.cell(0, 5, "Dot above = upper octave · Dot below = lower octave · "
                   "Underline = double speed (2×) · | divides angas · ‖ marks samam")

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
