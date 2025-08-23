import re

def render_guidelines_html(md_text: str) -> str:
    """
    Very small Markdown-ish to HTML with colorful callouts.
    Supports headings (#, ##), bold **...**, italics *...*,
    lists (- / 1.), and 'admonitions' like:
      [!IMPORTANT] Title
      body line 1
      body line 2

      Types: IMPORTANT, WARNING, TIP, INFO, NOTE
    """
    text = md_text or ""

    # Normalize newlines
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Convert admonitions blocks to HTML
    def adm_repl(match):
        kind = match.group("kind").upper()
        title = match.group("title").strip()
        body  = (match.group("body") or "").strip()
        return (
            f"<div class='kg-adm kg-{kind.lower()}'>"
            f"<div class='kg-adm-title'>{title}</div>"
            f"<div class='kg-adm-body'>{body.replace('\n','<br>')}</div>"
            f"</div>"
        )
    # Admonition regex: starts with [!TYPE] Title on a line, then optional body until blank line or end
    text = re.sub(
        r"^\s*\[\!(?P<kind>IMPORTANT|WARNING|TIP|INFO|NOTE)\]\s*(?P<title>[^\n]+)\n(?P<body>(?:.+\n)*?)(?:\n\s*\n|$)",
        adm_repl,
        text,
        flags=re.IGNORECASE | re.MULTILINE
    )

    # Bold / Italic (simple)
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<i>\1</i>", text)

    # Headings
    text = re.sub(r"^###\s*(.+)$", r"<h3 class='kg-h3'>\1</h3>", text, flags=re.MULTILINE)
    text = re.sub(r"^##\s*(.+)$",  r"<h2 class='kg-h2'>\1</h2>", text, flags=re.MULTILINE)
    text = re.sub(r"^#\s*(.+)$",   r"<h1 class='kg-h1'>\1</h1>", text, flags=re.MULTILINE)

    # Ordered / unordered lists
    # unordered
    lines = []
    in_ul = False
    for line in text.split("\n"):
        if re.match(r"^\s*-\s+.+", line):
            if not in_ul:
                lines.append("<ul class='kg-ul'>")
                in_ul = True
            lines.append("<li>" + re.sub(r"^\s*-\s+", "", line) + "</li>")
        else:
            if in_ul:
                lines.append("</ul>")
                in_ul = False
            lines.append(line)
    if in_ul: lines.append("</ul>")
    html = "\n".join(lines)

    # Paragraphs: wrap plain lines into <p>
    out_lines, buffer = [], []
    def flush_para():
        if buffer:
            out_lines.append("<p>" + "<br>".join(buffer) + "</p>")
            buffer.clear()
    for l in html.split("\n"):
        if l.strip() == "" or l.startswith("<") and not l.startswith("<p>"):
            flush_para()
            out_lines.append(l)
        else:
            buffer.append(l)
    flush_para()
    return "\n".join(out_lines)


GUIDELINES_CSS = """
<style>
.kg-wrap { line-height:1.6; font-size:0.98rem; }
.kg-h1 { font-size:1.25rem; font-weight:800; color:#0f5132; margin:.2rem 0 .4rem; }
.kg-h2 { font-size:1.1rem; font-weight:700; color:#14532d; margin:.6rem 0 .3rem; }
.kg-h3 { font-size:1.0rem; font-weight:700; color:#166534; margin:.4rem 0 .2rem; }
.kg-ul { margin:.25rem 0 .5rem .9rem; }
.kg-adm { border-radius:.75rem; padding:.6rem .8rem; margin:.5rem 0; border:1px solid transparent; }
.kg-adm-title { font-weight:700; margin-bottom:.2rem; }
.kg-adm-body { }
.kg-important { background:#fff5f5; border-color:#fecaca; }
.kg-warning  { background:#fffbeb; border-color:#fde68a; }
.kg-tip      { background:#ecfdf5; border-color:#a7f3d0; }
.kg-info     { background:#eff6ff; border-color:#bfdbfe; }
.kg-note     { background:#f5f3ff; border-color:#ddd6fe; }
.badge { display:inline-block; background:#065f46; color:#fff; padding:.15rem .5rem; border-radius:999px; font-size:.75rem; font-weight:700; letter-spacing:.5px; }
.kg-muted { color:#64748b; font-size:.9rem; }
</style>
"""
