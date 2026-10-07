import re
import pathlib

root = pathlib.Path(__file__).parent
files = {p.name for p in root.glob("*.md")}
anchors: dict[str, set[str]] = {}
bad: list[str] = []

CODE_FENCE = re.compile(r"```.*?```", re.S)
INLINE_CODE = re.compile(r"`[^`\n]*`")
HEADING = re.compile(r"^#+\s+(.+)$", re.M)
LINK = re.compile(r"\]\(([^)]+)\)")


def strip_code(text: str) -> str:
    text = CODE_FENCE.sub("", text)
    return INLINE_CODE.sub("", text)


for p in root.glob("*.md"):
    txt = strip_code(p.read_text(encoding="utf-8"))
    anchors[p.name] = set()
    for m in HEADING.finditer(txt):
        h = m.group(1).lower().strip()
        h = re.sub(r"[^\w\s-]", "", h, flags=re.U).strip().replace(" ", "-")
        anchors[p.name].add(h)

for p in root.glob("*.md"):
    txt = strip_code(p.read_text(encoding="utf-8"))
    for m in LINK.finditer(txt):
        link = m.group(1)
        if link.startswith("http"):
            continue
        target, _, frag = link.partition("#")
        if target:
            if target not in files:
                bad.append(f"{p.name}: missing file -> {link}")
            elif frag and frag not in anchors.get(target, set()):
                bad.append(f"{p.name}: missing anchor -> {link}")
        elif frag and frag not in anchors.get(p.name, set()):
            bad.append(f"{p.name}: missing local anchor -> {link}")

print("\n".join(bad) if bad else "ALL INTERNAL LINKS OK")
