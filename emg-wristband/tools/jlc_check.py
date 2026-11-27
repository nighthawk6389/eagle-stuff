#!/usr/bin/env python3
"""Read stock, library class and assembly type for LCSC part numbers from JLCPCB's public part pages.

Usage: jlc_check.py C527440 C37327670 ...        (prints a table)
       jlc_check.py --json out.json C527440 ...  (also saves the raw fields)

Only plain GETs of https://jlcpcb.com/partdetail/<C-number> are made, one per part.
"""
import json
import re
import subprocess
import sys
import time

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"


def fetch(code):
    r = subprocess.run(["curl", "-sS", "-L", "-m", "60", "-A", UA, f"https://jlcpcb.com/partdetail/{code}"],
                       capture_output=True)
    return r.stdout.decode("utf8", "replace")


def parse(code, page):
    out = {"lcsc": code}
    chunks = re.findall(r'self\.__next_f\.push\(\[1,"(.*?)"\]\)</script>', page, flags=re.S)
    payload = ""
    for c in chunks:
        try:
            payload += json.loads('"' + c + '"')
        except Exception:
            pass
    rec = None
    for m in re.finditer(r'"overseasStockCount"', payload):
        ls = payload.rfind("\n", 0, m.start()) + 1
        le = payload.find("\n", m.start())
        line = payload[ls:le if le > 0 else None]
        try:
            d = json.loads(line[line.find(":") + 1:])
        except Exception:
            continue
        if d.get("componentCode") == code:
            rec = d
            break
    if rec:
        out.update(mpn=rec.get("componentModelEn"), brand=rec.get("componentBrandEn"),
                   package=rec.get("componentSpecificationEn"), stock=rec.get("overseasStockCount"),
                   presale=rec.get("canPresaleNumber"), price=rec.get("initialPrice"),
                   lib=rec.get("componentLibraryType"), datasheet=rec.get("dataManualUrl"),
                   mode=rec.get("assemblyMode"))
    m = re.search(r'"describe":"([^"]*)"', payload)
    if m:
        out["desc"] = m.group(1)
    m = re.search(r'PCBA Type</dt><dd[^>]*>(?:<[^>]+>)*([^<]+)<', page)
    out["pcba_type"] = m.group(1).strip() if m else None
    m = re.search(r'Assembly Type</dt><dd[^>]*>(?:<[^>]+>)*([^<]+)<', page)
    out["assembly"] = m.group(1).strip() if m else None
    m = re.search(r'"preferredComponentFlag":(true|false)', payload)
    out["preferred"] = (m.group(1) == "true") if m else None
    return out


def main(argv):
    save = None
    if argv and argv[0] == "--json":
        save, argv = argv[1], argv[2:]
    rows = []
    for code in argv:
        page = fetch(code)
        rows.append(parse(code, page))
        time.sleep(0.4)
    for r in rows:
        lib = {"base": "Basic", "expand": "Extended"}.get(r.get("lib"), r.get("lib"))
        if r.get("preferred"):
            lib = f"{lib}+Pref"
        print(f"{r['lcsc']:<10} {str(r.get('mpn')):<28.28} {str(r.get('brand')):<16.16} {str(r.get('package')):<18.18} "
              f"stock={str(r.get('stock')):<8} {str(lib):<9} {str(r.get('pcba_type')):<22} ${r.get('price')}")
    if save:
        json.dump(rows, open(save, "w"), indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main(sys.argv[1:])
