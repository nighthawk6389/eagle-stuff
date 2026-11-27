"""Compare the netlist KiCad exports from the schematic with the intended netlist."""
import re


def read_netlist(path):
    text = open(path, encoding="utf8").read()
    nets = {}
    start = text.index("(nets")
    for m in re.finditer(r'\(net \(code "?\d+"?\) \(name "([^"]*)"\)(.*?)(?=\(net \(code|\Z)', text[start:], flags=re.S):
        name = m.group(1)
        for ref, pin in re.findall(r'\(node \(ref "([^"]+)"\) \(pin "([^"]+)"\)', m.group(2)):
            nets[(ref, pin)] = name
    return nets


def normal(name):
    if name.startswith("unconnected-"):
        return None
    return name.rsplit("/", 1)[-1]


def compare(path, intended):
    got = {k: normal(v) for k, v in read_netlist(path).items() if not k[0].startswith("#")}
    problems = []
    for key, net in sorted(intended.items()):
        if key not in got:
            if net is not None:
                problems.append(f"{key[0]} pin {key[1]}: expected {net}, pin missing from KiCad netlist")
        elif got[key] != net:
            problems.append(f"{key[0]} pin {key[1]}: expected {net}, schematic has {got[key]}")
    for key in sorted(got):
        if key not in intended:
            problems.append(f"{key[0]} pin {key[1]}: on {got[key]} in the schematic but not in the design tables")
    return problems
