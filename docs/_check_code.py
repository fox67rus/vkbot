import ast
import pathlib
import re

root = pathlib.Path(__file__).parent
BLOCK = re.compile(r"```(\w*)\n(.*?)```", re.S)

total = 0
parsed = 0
fragments: list[str] = []


def try_parse(code: str) -> bool:
    """Try the snippet as-is, then wrapped in an async function, then as an expression."""
    candidates = [code]
    indented = "\n".join("    " + line for line in code.splitlines())
    candidates.append("async def _f():\n" + indented)
    candidates.append("def _f():\n" + indented)
    for cand in candidates:
        try:
            ast.parse(cand)
            return True
        except SyntaxError:
            continue
    return False


for p in sorted(root.glob("*.md")):
    if p.name.startswith("_"):
        continue
    txt = p.read_text(encoding="utf-8")
    for i, m in enumerate(BLOCK.finditer(txt), 1):
        lang, code = m.group(1), m.group(2)
        if lang not in ("python", "py"):
            continue
        total += 1
        if try_parse(code):
            parsed += 1
        else:
            fragments.append(f"{p.name} block#{i}: {code.strip().splitlines()[0][:90]}")

print(f"python blocks: {total}, parsed OK: {parsed}, fragments: {len(fragments)}")
if fragments:
    print("\n--- fragments (неполные куски из документации) ---")
    print("\n".join(fragments))
