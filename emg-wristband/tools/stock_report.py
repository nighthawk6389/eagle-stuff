#!/usr/bin/env python3
"""Check every BOM line against JLCPCB's public part pages and write out/stock-check.md.

Usage: python3 tools/stock_report.py [boards]      (boards defaults to 2, JLCPCB's assembly minimum)
Exits non-zero if a part is out of stock or the page shows a different part. Parts marked
"Standard Only" are allowed (the order uses Standard assembly) and are listed at the end.
"""
import csv
import datetime
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import jlc_check  # noqa: E402

ROOT = os.path.dirname(HERE)


def main():
    boards = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    rows = list(csv.DictReader(open(os.path.join(ROOT, "out", "bom-jlcpcb.csv"))))
    lines = ["# JLCPCB stock and assembly-type check", "",
             f"Read from jlcpcb.com part pages on {datetime.date.today().isoformat()} "
             f"by `tools/stock_report.py`, for {boards} boards.", "",
             "| LCSC | Part (JLCPCB page) | Package | Used as | Per board | Stock | Library | Assembly type | Unit USD | OK |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    bad = 0
    standard = []
    for row in rows:
        code = row["LCSC Part #"]
        r = jlc_check.parse(code, jlc_check.fetch(code))
        time.sleep(0.4)
        need = int(row["Quantity"]) * boards
        stock = r.get("stock") or 0
        mpn_ok = (r.get("mpn") or "").replace(" ", "").upper().startswith(row["Manufacturer Part"].split()[-1].replace(" ", "").upper()[:8]) \
            or row["Manufacturer Part"].replace(" ", "").upper().startswith((r.get("mpn") or "?").replace(" ", "").upper()[:8])
        ok = stock >= need and r.get("pcba_type") in ("Economic and Standard", "Standard Only") and mpn_ok
        if r.get("pcba_type") == "Standard Only":
            standard.append(f"{code} ({row['Comment']})")
        bad += not ok
        lib = {"base": "Basic", "expand": "Extended"}.get(r.get("lib"), str(r.get("lib")))
        lines.append(f"| {code} | {r.get('mpn')} ({r.get('brand')}) | {r.get('package')} | {row['Comment']} | "
                     f"{row['Quantity']} | {stock} | {lib} | {r.get('pcba_type')} | {r.get('price')} | "
                     f"{'yes' if ok else 'NO'} |")
    ext = sum(1 for l in lines[6:] if "| Extended |" in l)
    lines += ["", f"{len(rows)} BOM lines, {ext} of them extended parts (JLCPCB charges a fee per extended part type).",
              "Parts that force Standard assembly: " + (", ".join(standard) or "none") + ".",
              "Not on the BOM: the test points and the motor pads (bare copper), and the motor itself."]
    open(os.path.join(ROOT, "out", "stock-check.md"), "w").write("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
