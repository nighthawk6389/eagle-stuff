#!/usr/bin/env python3
"""Generate the KiCad project in ../pod, then check and export it.

    python3 gen/build.py            generate, run ERC, compare the netlist, export PDF and BOM
    python3 gen/build.py --no-kicad generate the files only (no kicad-cli needed)
"""
import csv
import datetime
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import check      # noqa: E402
import design     # noqa: E402
import kisch      # noqa: E402

ROOT = os.path.dirname(HERE)
POD = os.path.join(ROOT, "pod")
OUT = os.path.join(ROOT, "out")
DATE = "2026-11-27"


def write_project():
    os.makedirs(os.path.join(POD, "lib", "emgpod.pretty"), exist_ok=True)
    os.makedirs(OUT, exist_ok=True)
    kisch.write_custom_library(os.path.join(POD, "lib", "emgpod.kicad_sym"))
    with open(os.path.join(POD, "sym-lib-table"), "w") as f:
        f.write('(sym_lib_table\n\t(version 7)\n\t(lib (name "emgpod")(type "KiCad")'
                '(uri "${KIPRJMOD}/lib/emgpod.kicad_sym")(options "")(descr "Symbols used by the pod"))\n)\n')
    with open(os.path.join(POD, "fp-lib-table"), "w") as f:
        f.write('(fp_lib_table\n\t(version 7)\n\t(lib (name "emgpod")(type "KiCad")'
                '(uri "${KIPRJMOD}/lib/emgpod.pretty")(options "")(descr "Seeed XIAO footprint and a bare test pad"))\n)\n')
    pro = os.path.join(POD, "emg-pod.kicad_pro")
    if not os.path.exists(pro):
        with open(pro, "w") as f:
            json.dump({"meta": {"filename": "emg-pod.kicad_pro", "version": 3}, "schematic": {}, "sheets": [],
                       "text_variables": {}}, f, indent=2)
            f.write("\n")


def write_bom():
    groups = {}
    for ref, (value, fp, lcsc, mpn) in design.BOM.items():
        groups.setdefault((lcsc, value, fp, mpn), []).append(ref)

    def key(r):
        head = r.rstrip("0123456789")
        return head, int(r[len(head):])
    rows = sorted(groups.items(), key=lambda kv: key(sorted(kv[1], key=key)[0]))
    with open(os.path.join(OUT, "bom-jlcpcb.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Comment", "Designator", "Footprint", "LCSC Part #", "Manufacturer Part", "Quantity"])
        for (lcsc, value, fp, mpn), refs in rows:
            refs = sorted(refs, key=key)
            w.writerow([value, ",".join(refs), fp.split(":")[1], lcsc, mpn, len(refs)])
    return rows


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=POD)
    return r.returncode, (r.stdout + r.stderr).strip()


def main():
    for f in os.listdir(POD) if os.path.isdir(POD) else []:
        if f.endswith(".kicad_sch"):
            os.remove(os.path.join(POD, f))
    os.makedirs(POD, exist_ok=True)
    design.build(POD, DATE)
    write_project()
    rows = write_bom()
    print(f"{len(design.BOM)} parts to assemble on {len(rows)} BOM lines; {len(design.NET)} pins in the netlist")
    if "--no-kicad" in sys.argv:
        return 0
    code, out = run(["kicad-cli", "sch", "erc", "--severity-all", "--exit-code-violations",
                     "-o", os.path.join(OUT, "erc.rpt"), "emg-pod.kicad_sch"])
    print("ERC:", out.splitlines()[0] if out else "", "(exit %d)" % code)
    ok = code == 0
    net = os.path.join(OUT, "emg-pod.net")
    run(["kicad-cli", "sch", "export", "netlist", "--format", "kicadsexpr", "-o", net, "emg-pod.kicad_sch"])
    problems = check.compare(net, design.NET)
    os.remove(net)
    print("Netlist check:", "matches the design tables" if not problems else f"{len(problems)} PROBLEMS")
    for p in problems[:40]:
        print("   ", p)
    ok = ok and not problems
    code, out = run(["kicad-cli", "sch", "export", "pdf", "-o", os.path.join(OUT, "emg-pod-schematic.pdf"),
                     "emg-pod.kicad_sch"])
    print("PDF:", "written" if code == 0 else out)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
