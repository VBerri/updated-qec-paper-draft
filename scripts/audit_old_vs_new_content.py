from pathlib import Path
import re
from pypdf import PdfReader

root = Path("c:/Me/qec_repetition_research")
old_pdf = root / "papers" / "82050234-e67f-4961-a72d-2337fae66dbd (5).pdf"
new_pdf = root / "papers" / "qec_repetition_three_stage.pdf"
tex_path = root / "papers" / "qec_repetition_three_stage.tex"


def extract_text(path: Path) -> str:
    reader = PdfReader(str(path))
    return "\n".join((page.extract_text() or "") for page in reader.pages)


def norm(text: str) -> str:
    return re.sub(r"\s+", " ", text).lower()


old_text = norm(extract_text(old_pdf))
new_text = norm(extract_text(new_pdf))
tex_text = tex_path.read_text(encoding="utf-8")

keywords = [
    "bit-flip",
    "phase-flip",
    "depolarizing",
    "logical success",
    "logical error",
    "majority",
    "mwpm",
    "pymatching",
    "stim",
    "ibm",
    "ibm_fez",
    "repeatability",
    "heterogeneous",
    "temporal drift",
    "bias",
    "theory",
    "baseline",
    "limitations",
    "conclusion",
]

print("KEYWORD_COVERAGE old/new")
for keyword in keywords:
    old_has = "Y" if keyword in old_text else "N"
    new_has = "Y" if keyword in new_text else "N"
    print(f"{keyword}: {old_has}/{new_has}")

sections = re.findall(r"\\section\{([^}]*)\}|\\subsection\{([^}]*)\}", tex_text)
print("\nNEW_TEX_SECTIONS")
for sec, subsec in sections:
    print("-", sec or subsec)

checks = [
    "bitflip_summary.tex",
    "phaseflip_summary.tex",
    "depolarizing_summary.tex",
    "bitflip_success.png",
    "phaseflip_success.png",
    "depolarizing_success.png",
]
print("\nLEGACY_ASSET_WIRING")
for check in checks:
    print(check, "Y" if check in tex_text else "N")
