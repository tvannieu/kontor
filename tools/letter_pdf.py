#!/usr/bin/env python3
"""
letter_pdf.py - DIN 5008 (form B) letter generator, standard library only.

Writes an A4 PDF whose address field sits in the window of a DL envelope when
the sheet is folded in thirds. No external dependencies: Helvetica is one of
the 14 standard PDF fonts that every viewer ships with, and the PDF is written
by hand.

Usage:
    KONTOR_LETTER_CONFIG=/path/outside/any/repo/letter.conf \
        python3 letter_pdf.py letter.txt letter.pdf

Requirements:
    Python 3.8+. Nothing else.

Configuration (required):
    The sender block, place and optional contact lines are NOT part of this
    script. They are read from a file whose path is given in the environment
    variable KONTOR_LETTER_CONFIG. Keep that file outside every repository.
    If the variable is unset or the file is missing or incomplete, the script
    stops with an error; it never falls back to a default sender.

    Config format, one `key: value` per line, `#` starts a comment:

        sender: Example Sender | Sample Street 1 | 12345 Sampletown
        place: Sampletown
        phone: +00 000 0000000        (optional)
        email: <your e-mail address>  (optional)

    The first `sender` field is the name printed under the signature line.
    See letter.conf.example.

Source file format:
    Header lines `Key: value`, one empty line, then the letter body.

        Recipient: Example Court | Sample Avenue 2 | 12345 Sampletown
        Date: 8 September 2026
        Subject: Withdrawal of the application
        Reference: File no. X 1/26
        Enclosure: Withdrawal form

        Sehr geehrte Damen und Herren,
        ...

    Optional keys: Reference2, Window (dl | c4 | none), Font-Size, Line-Height,
    Paragraph-Gap, Justify (block | ragged).
    Wrap text in **double asterisks** for bold. A line containing only `--`
    draws the signature line and prints the sender name below it; do not type
    the name again after it.

    Window positions are not standardised across envelope makers. Before
    posting, hold the sheet against the envelope and look through the window.

Labels and body stay German on purpose: the DIN 5008 letter itself is German.
"""

import os
import sys

MM = 2.834645669  # points per millimetre
A4_W, A4_H = 595.276, 841.890

# Helvetica glyph widths in 1/1000 em, as far as German mail needs them.
_W = {}
for c in "0123456789":
    _W[c] = 556
for c, w in {
    " ": 278, "!": 278, '"': 355, "#": 556, "$": 556, "%": 889, "&": 667,
    "'": 191, "(": 333, ")": 333, "*": 389, "+": 584, ",": 278, "-": 333,
    ".": 278, "/": 278, ":": 278, ";": 278, "<": 584, "=": 584, ">": 584,
    "?": 556, "@": 1015, "[": 278, "\\": 278, "]": 278, "^": 469, "_": 556,
    "`": 333, "{": 334, "|": 260, "}": 334, "~": 584,
    "A": 667, "B": 667, "C": 722, "D": 722, "E": 667, "F": 611, "G": 778,
    "H": 722, "I": 278, "J": 500, "K": 667, "L": 556, "M": 833, "N": 722,
    "O": 778, "P": 667, "Q": 778, "R": 722, "S": 667, "T": 611, "U": 722,
    "V": 667, "W": 944, "X": 667, "Y": 667, "Z": 611,
    "a": 556, "b": 556, "c": 500, "d": 556, "e": 556, "f": 278, "g": 556,
    "h": 556, "i": 222, "j": 222, "k": 500, "l": 222, "m": 833, "n": 556,
    "o": 556, "p": 556, "q": 556, "r": 333, "s": 500, "t": 278, "u": 556,
    "v": 500, "w": 722, "x": 500, "y": 500, "z": 500,
    "ä": 556, "ö": 556, "ü": 556, "Ä": 667, "Ö": 778,
    "Ü": 722, "ß": 556, "§": 556, "°": 400, "€": 556,
    "é": 556, "è": 556, "«": 556, "»": 556, "–": 556,
    "—": 1000, "„": 333, "“": 333, "’": 191, "·": 278,
}.items():
    _W[c] = w

# Helvetica-Bold has its own widths. A flat surcharge is not enough: it
# underestimates wide lowercase letters by up to ten percent, and the
# accumulated error eats the following space at the end of a word.
_WB = {}
for c in "0123456789":
    _WB[c] = 556
for c, w in {
    " ": 278, "!": 333, '"': 474, "#": 556, "$": 556, "%": 889, "&": 722,
    "'": 238, "(": 333, ")": 333, "*": 389, "+": 584, ",": 278, "-": 333,
    ".": 278, "/": 278, ":": 333, ";": 333, "<": 584, "=": 584, ">": 584,
    "?": 611, "@": 975, "[": 333, "\\": 278, "]": 333, "^": 584, "_": 556,
    "`": 333, "{": 389, "|": 280, "}": 389, "~": 584,
    "A": 722, "B": 722, "C": 722, "D": 722, "E": 667, "F": 611, "G": 778,
    "H": 722, "I": 278, "J": 556, "K": 722, "L": 611, "M": 833, "N": 722,
    "O": 778, "P": 667, "Q": 778, "R": 722, "S": 667, "T": 611, "U": 722,
    "V": 667, "W": 944, "X": 667, "Y": 667, "Z": 611,
    "a": 556, "b": 611, "c": 556, "d": 611, "e": 556, "f": 333, "g": 611,
    "h": 611, "i": 278, "j": 278, "k": 556, "l": 278, "m": 889, "n": 611,
    "o": 611, "p": 611, "q": 611, "r": 389, "s": 556, "t": 333, "u": 611,
    "v": 556, "w": 778, "x": 556, "y": 556, "z": 500,
    "ä": 556, "ö": 611, "ü": 611, "Ä": 722, "Ö": 778,
    "Ü": 722, "ß": 611, "§": 556, "°": 400, "€": 556,
    "é": 556, "è": 556, "«": 556, "»": 556, "–": 556,
    "—": 1000, "„": 500, "“": 500, "’": 238, "·": 278,
}.items():
    _WB[c] = w


def width(text, size, bold=False):
    tab = _WB if bold else _W
    return sum(tab.get(ch, 556) for ch in text) / 1000.0 * size


def wrap(text, size, max_w, bold=False):
    """Wrap at max_w. An empty string yields one empty line."""
    if not text.strip():
        return [""]
    lines, cur = [], ""
    for word in text.split():
        probe = word if not cur else cur + " " + word
        if width(probe, size, bold) <= max_w:
            cur = probe
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def parse_runs(text):
    """Split a paragraph into runs; **text marked like this** becomes bold."""
    runs = []
    for i, part in enumerate(text.split("**")):
        if part:
            runs.append((part, i % 2 == 1))
    return runs or [("", False)]


def _words(runs):
    """Split runs into words. A word may consist of several segments, so that
    a punctuation mark directly after a bold span stays attached instead of
    becoming a separate word with a space in front."""
    words = []
    open_end = False       # the previous segment ended without a space
    for text, bold in runs:
        pieces = text.split(" ")
        for k, seg in enumerate(pieces):
            if not seg:
                continue
            if k == 0 and open_end and words:
                words[-1].append((seg, bold))
            else:
                words.append([(seg, bold)])
        open_end = not text.endswith(" ")
    return words


def _word_width(word, size):
    return sum(width(t, size, b) for t, b in word)


def wrap_runs(runs, size, max_w):
    """Like wrap(), but across bold spans. Returns lines of words, each word a
    list of (text, bold) segments."""
    lines, cur, cur_w = [], [], 0.0
    for word in _words(runs):
        ww = _word_width(word, size)
        sp = width(" ", size, cur[-1][-1][1]) if cur else 0.0
        if cur and cur_w + sp + ww > max_w:
            lines.append(cur)
            cur, cur_w = [word], ww
        else:
            cur.append(word)
            cur_w += sp + ww
    if cur:
        lines.append(cur)
    return lines or [[]]


def esc(text):
    out = []
    for ch in text:
        if ch in "()\\":
            out.append("\\" + ch)
        elif ord(ch) < 128:
            out.append(ch)
        else:
            try:
                out.append("\\%03o" % _WINANSI[ch])
            except KeyError:
                out.append("?")
    return "".join(out)


# WinAnsiEncoding for the non-ASCII characters used here.
_WINANSI = {
    "ä": 0xE4, "ö": 0xF6, "ü": 0xFC, "Ä": 0xC4,
    "Ö": 0xD6, "Ü": 0xDC, "ß": 0xDF, "§": 0xA7,
    "°": 0xB0, "€": 0x80, "é": 0xE9, "è": 0xE8,
    "«": 0xAB, "»": 0xBB, "–": 0x96, "—": 0x97,
    "„": 0x84, "“": 0x93, "’": 0x92, "·": 0xB7,
}


class Page:
    def __init__(self):
        self.ops = []

    def text(self, x_mm, y_mm, s, size=11, bold=False):
        """y_mm counts downwards from the top edge of the sheet."""
        if not s:
            return
        font = "F2" if bold else "F1"
        y = A4_H - y_mm * MM
        self.ops.append(
            "BT /%s %.1f Tf 1 0 0 1 %.2f %.2f Tm (%s) Tj ET"
            % (font, size, x_mm * MM, y, esc(s))
        )

    def text_runs(self, x_mm, y_mm, line, size=11, gap_extra=0.0):
        """Draw a line of words; a word may have several segments with
        different emphasis. `gap_extra` is the additional space per word gap
        in millimetres; that is what produces justified text."""
        x = x_mm
        for i, word in enumerate(line):
            if i:
                x += width(" ", size, word[0][1]) / MM + gap_extra
            for t, b in word:
                self.text(x, y_mm, t, size, b)
                x += width(t, size, b) / MM

    def text_right(self, x_mm, y_mm, s, size=11, bold=False):
        self.text(x_mm - width(s, size, bold) / MM, y_mm, s, size, bold)

    def line(self, x1_mm, y_mm, x2_mm):
        y = A4_H - y_mm * MM
        self.ops.append(
            "%.2f %.2f m %.2f %.2f l 0.6 w S" % (x1_mm * MM, y, x2_mm * MM, y)
        )

    def stream(self):
        # White page background: some viewers and converters render a PDF
        # page without its own background as black.
        bg = "1 1 1 rg 0 0 %.2f %.2f re f 0 g" % (A4_W, A4_H)
        return "\n".join([bg] + self.ops)


def build_pdf(pages, path):
    objs = []

    def add(body):
        objs.append(body)
        return len(objs)  # 1-based

    kids = []
    page_ids = []
    content_ids = []
    for p in pages:
        data = p.stream().encode("latin-1")
        content_ids.append(add(b"<< /Length %d >>\nstream\n" % len(data) + data + b"\nendstream"))
    font1 = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
    font2 = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>")
    pages_id = len(objs) + len(pages) + 1
    for cid in content_ids:
        page_ids.append(add(
            ("<< /Type /Page /Parent %d 0 R /MediaBox [0 0 %.3f %.3f] "
             "/Resources << /Font << /F1 %d 0 R /F2 %d 0 R >> >> /Contents %d 0 R >>"
             % (pages_id, A4_W, A4_H, font1, font2, cid)).encode("latin-1")))
    kids = " ".join("%d 0 R" % i for i in page_ids)
    add(("<< /Type /Pages /Kids [%s] /Count %d >>" % (kids, len(page_ids))).encode("latin-1"))
    root = add(("<< /Type /Catalog /Pages %d 0 R >>" % pages_id).encode("latin-1"))

    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for i, body in enumerate(objs, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % i + body + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n" % (len(objs) + 1)
    out += b"0000000000 65535 f \n"
    for off in offsets[1:]:
        out += b"%010d 00000 n \n" % off
    out += (b"trailer\n<< /Size %d /Root %d 0 R >>\nstartxref\n%d\n%%%%EOF\n"
            % (len(objs) + 1, root, xref))
    with open(path, "wb") as f:
        f.write(bytes(out))


# --- Page geometry -----------------------------------------------------------
LEFT = 25.0          # left margin in mm
RIGHT = 190.0        # right text edge in mm
TEXT_W = (RIGHT - LEFT) * MM
BODY_SIZE = 11.0
LEAD = 5.6           # line spacing in mm
BOTTOM = 275.0       # end of text in mm; hardly any printer prints below


ENV_VAR = "KONTOR_LETTER_CONFIG"


def load_config():
    """Read the sender configuration from the file named in ENV_VAR.
    Exits with a clear message if it is missing or incomplete; there is
    deliberately no default sender."""
    path = os.environ.get(ENV_VAR)
    if not path:
        sys.exit("error: environment variable %s is not set. It must point to "
                 "a config file outside any repository (see the header of "
                 "this script and letter.conf.example)." % ENV_VAR)
    try:
        with open(os.path.expanduser(path), encoding="utf-8") as f:
            lines = f.read().splitlines()
    except OSError as e:
        sys.exit("error: cannot read config file %s: %s" % (path, e))
    cfg = {}
    for line in lines:
        line = line.split("#", 1)[0].strip()
        if ":" in line:
            k, v = line.split(":", 1)
            cfg[k.strip().lower()] = v.strip()
    for required in ("sender", "place"):
        if not cfg.get(required):
            sys.exit("error: config file %s has no '%s:' line." % (path, required))
    return cfg


def render(meta, body_lines, path, cfg):
    sender = [a.strip() for a in cfg["sender"].split("|")]
    recipient = [e.strip() for e in meta.get("Recipient", "").split("|") if e.strip()]
    place = cfg["place"]

    pages = [Page()]
    p = pages[0]

    # Sender block, top right, outside the window
    y = 22.0
    for i, ln in enumerate(sender):
        p.text_right(RIGHT, y, ln, 9.5, bold=(i == 0))
        y += 4.4
    for extra in ("phone", "email"):
        if cfg.get(extra):
            p.text_right(RIGHT, y, cfg[extra], 9.5)
            y += 4.4

    # Address field. dl = DIN 5008 form B, 45 mm from the top, for DL
    # envelopes (A4 folded in thirds). c4 = 58 mm, for C4 (A4 unfolded).
    # none = no address field; the address then goes into the body.
    # Window positions are not standardised: before posting, hold the sheet
    # against the envelope and look through the window.
    window = meta.get("Window", "dl").strip().lower()
    TOP = {"dl": 45.0, "c4": 58.0}
    if window in TOP and recipient:
        p.text(LEFT, TOP[window], " · ".join(sender), 7.0)
        y = TOP[window] + 6.0
        for ln in recipient:
            p.text(LEFT, y, ln, 11.0)
            y += 5.0

    # Date in the information block right of the address field. The window is
    # only 90 mm wide and starts 20 mm from the left edge, so a date set
    # right-aligned at 190 mm is safely outside it.
    if meta.get("Date"):
        p.text_right(RIGHT, TOP.get(window, 45.0) + 6.0,
                     place + ", " + meta["Date"], 10.5)

    # Reference lines and subject, both below the window (which ends at 90 mm)
    y = (TOP[window] + 51.0) if window in TOP else 60.0
    for key in ("Reference", "Reference2"):
        if meta.get(key):
            # Wrap long file-number lines instead of running over the margin.
            for ln in wrap(meta[key], 10.0, TEXT_W):
                p.text(LEFT, y, ln, 10.0)
                y += 4.8
    if meta.get("Subject"):
        y += 3.0
        for ln in wrap(meta["Subject"], 11.5, TEXT_W, bold=True):
            p.text(LEFT, y, ln, 11.5, bold=True)
            y += 5.4

    size = float(meta.get("Font-Size", BODY_SIZE))
    lead = float(meta.get("Line-Height", LEAD))
    para = float(meta.get("Paragraph-Gap", 2.4))
    justify = meta.get("Justify", "block").strip().lower() != "ragged"

    y += 7.0
    while body_lines and not body_lines[-1].strip():
        body_lines.pop()
    for raw in body_lines:
        if raw.strip() == "--":
            # Never cut the signature block: it needs about 20 mm.
            if y + 20.0 > BOTTOM:
                pages.append(Page())
                p = pages[-1]
                y = 25.0
            y += 9.0
            p.line(LEFT, y, LEFT + 70)
            y += 4.6
            p.text(LEFT, y, sender[0], size)
            y += lead
            continue
        lines = wrap_runs(parse_runs(raw), size, TEXT_W)
        for idx, line in enumerate(lines):
            if y > BOTTOM and line:
                pages.append(Page())
                p = pages[-1]
                y = 25.0
            # Justified text: all lines of a paragraph except the last are
            # stretched to the full width. The last line stays left-aligned,
            # otherwise the typical gaps appear.
            gap = 0.0
            if justify and idx < len(lines) - 1 and len(line) > 1:
                natural = sum(width(t, size, b) for w in line for t, b in w)
                natural += sum(width(" ", size, w[0][1]) for w in line[1:])
                missing = TEXT_W - natural
                if missing > 0:
                    gap = missing / (len(line) - 1) / MM
                    # Avoid the zipper effect: rather leave a very loose line
                    # ragged than stretch it extremely.
                    if gap > 2.5:
                        gap = 0.0
            p.text_runs(LEFT, y, line, size, gap)
            y += lead
        if not raw.strip():
            continue
        y += para

    if meta.get("Enclosure"):
        y += 2.0
        if y > BOTTOM:
            pages.append(Page())
            p = pages[-1]
            y = 25.0
        # The enclosure line may run close to the print margin; it is short
        # and a separate page break for it would cost more than a few mm.
        # The label "Anlage" is the German DIN 5008 field label.
        for i, ln in enumerate(wrap(meta["Enclosure"], 10.5, TEXT_W - 16)):
            if y > 284.0:
                pages.append(Page())
                p = pages[-1]
                y = 25.0
            p.text(LEFT, y, ("Anlage: " if i == 0 else "        ") + ln, 10.5)
            y += 4.9

    build_pdf(pages, path)
    return len(pages)


def main():
    if len(sys.argv) != 3:
        sys.exit("usage: %s letter.txt letter.pdf  (needs %s, see header)"
                 % (sys.argv[0], ENV_VAR))
    cfg = load_config()
    src, dst = sys.argv[1], sys.argv[2]
    with open(src, encoding="utf-8") as f:
        raw = f.read()
    head, _, body = raw.partition("\n\n")
    meta = {}
    for line in head.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip()
    n = render(meta, body.split("\n"), dst, cfg)
    print("%s: %d page(s)" % (dst, n))


if __name__ == "__main__":
    main()
