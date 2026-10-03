from pathlib import Path
import csv
import sys

from pypdf import PdfReader

root = Path("c:/Me/qec_repetition_research")
old_pdf = root / "papers" / "82050234-e67f-4961-a72d-2337fae66dbd (5).pdf"
new_pdf = root / "papers" / "qec_repetition_three_stage.pdf"


def pdf_text(path: Path) -> str:
    reader = PdfReader(str(path))
    return "\n".join((p.extract_text() or "") for p in reader.pages)


if not old_pdf.exists():
    print("MISSING_OLD_PDF", old_pdf)
    sys.exit(1)
if not new_pdf.exists():
    print("MISSING_NEW_PDF", new_pdf)
    sys.exit(1)

old_text = pdf_text(old_pdf)
new_text = pdf_text(new_pdf)

key_values = [
    "0.9225", "0.9820", "0.9980",
    "0.8625", "0.9465", "0.9755",
    "0.8095", "0.8900", "0.9460",
    "0.7625", "0.8440", "0.8915",
    "0.9620", "0.9960", "0.9995",
    "0.9805", "0.9950", "0.9815",
]

print("PDF_PATHS")
print("OLD=", old_pdf)
print("NEW=", new_pdf)

print("\nKEY_VALUE_PRESENCE")
for value in key_values:
    print(f"{value}: old={'Y' if value in old_text else 'N'} new={'Y' if value in new_text else 'N'}")

bit = list(csv.DictReader(open(root / "qiskit-qec-noise-sim/results/bitflip_results.csv", newline="", encoding="utf-8")))
ph = list(csv.DictReader(open(root / "qiskit-qec-noise-sim/results/phaseflip_results.csv", newline="", encoding="utf-8")))
dep = list(csv.DictReader(open(root / "qiskit-qec-noise-sim/results/depolarizing_results.csv", newline="", encoding="utf-8")))

ps = {0.0, 0.02, 0.04, 0.06, 0.08}
targets = {
    ("bitflip", 1, 0.02): 0.9225, ("bitflip", 3, 0.02): 0.9820, ("bitflip", 5, 0.02): 0.9980,
    ("bitflip", 1, 0.04): 0.8625, ("bitflip", 3, 0.04): 0.9465, ("bitflip", 5, 0.04): 0.9755,
    ("bitflip", 1, 0.06): 0.8095, ("bitflip", 3, 0.06): 0.8900, ("bitflip", 5, 0.06): 0.9460,
    ("bitflip", 1, 0.08): 0.7625, ("bitflip", 3, 0.08): 0.8440, ("bitflip", 5, 0.08): 0.8915,
    ("phaseflip", 1, 0.02): 0.9225, ("phaseflip", 3, 0.02): 0.9820, ("phaseflip", 5, 0.02): 0.9980,
    ("phaseflip", 1, 0.04): 0.8625, ("phaseflip", 3, 0.04): 0.9465, ("phaseflip", 5, 0.04): 0.9755,
    ("phaseflip", 1, 0.06): 0.8095, ("phaseflip", 3, 0.06): 0.8900, ("phaseflip", 5, 0.06): 0.9460,
    ("phaseflip", 1, 0.08): 0.7625, ("phaseflip", 3, 0.08): 0.8440, ("phaseflip", 5, 0.08): 0.8915,
    ("depolarizing", 1, 0.02): 0.9620, ("depolarizing", 3, 0.02): 0.9960, ("depolarizing", 5, 0.02): 0.9995,
    ("depolarizing", 1, 0.04): 0.9225, ("depolarizing", 3, 0.04): 0.9805, ("depolarizing", 5, 0.04): 0.9965,
    ("depolarizing", 1, 0.06): 0.8935, ("depolarizing", 3, 0.06): 0.9670, ("depolarizing", 5, 0.06): 0.9950,
    ("depolarizing", 1, 0.08): 0.8625, ("depolarizing", 3, 0.08): 0.9440, ("depolarizing", 5, 0.08): 0.9815,
}

actual = {}
for row in bit:
    p = round(float(row["p"]), 2)
    if p in ps:
        actual[("bitflip", int(row["n"]), p)] = float(row["success"])
for row in ph:
    p = round(float(row["p"]), 2)
    if p in ps:
        actual[("phaseflip", int(row["n"]), p)] = float(row["success"])
for row in dep:
    p = round(float(row["p"]), 2)
    if p not in ps:
        continue
    method = row["method"]
    if method == "baseline_n1":
        actual[("depolarizing", 1, p)] = float(row["success"])
    elif method == "phaseflip_rep_n3":
        actual[("depolarizing", 3, p)] = float(row["success"])
    elif method == "phaseflip_rep_n5":
        actual[("depolarizing", 5, p)] = float(row["success"])

ok = 0
bad = []
for key, expected in targets.items():
    observed = actual.get(key)
    if observed is None:
        bad.append((key, expected, None))
    elif abs(observed - expected) < 1e-9:
        ok += 1
    else:
        bad.append((key, expected, observed))

print("\nCSV_VS_OLD_TABLE_CHECK")
print("TARGET_POINTS=", len(targets), "EXACT_MATCH=", ok, "MISMATCH=", len(bad))
if bad:
    for item in bad[:20]:
        print("MISMATCH", item)

missing_in_new = [v for v in key_values if v not in new_text]
print("\nNEW_PDF_OLD_VALUE_COVERAGE")
print("OLD_KEY_VALUES_TOTAL=", len(key_values), "PRESENT_IN_NEW=", len(key_values) - len(missing_in_new), "MISSING_IN_NEW=", len(missing_in_new))
if missing_in_new:
    print("MISSING_VALUES_IN_NEW", ", ".join(missing_in_new))
