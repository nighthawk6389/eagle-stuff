"""Minimal S-expression reader/writer for KiCad files."""


class Q(str):
    """A quoted string atom."""


def parse(text):
    pos = 0
    n = len(text)
    stack = [[]]
    while pos < n:
        c = text[pos]
        if c in " \t\r\n":
            pos += 1
        elif c == "(":
            new = []
            stack[-1].append(new)
            stack.append(new)
            pos += 1
        elif c == ")":
            stack.pop()
            pos += 1
        elif c == '"':
            j = pos + 1
            buf = []
            while text[j] != '"':
                if text[j] == "\\":
                    nxt = text[j + 1]
                    buf.append({"n": "\n", "t": "\t", "r": "\r"}.get(nxt, nxt))
                    j += 2
                else:
                    buf.append(text[j])
                    j += 1
            stack[-1].append(Q("".join(buf)))
            pos = j + 1
        else:
            j = pos
            while j < n and text[j] not in " \t\r\n()":
                j += 1
            stack[-1].append(text[pos:j])
            pos = j
    return stack[0][0]


def _atom(a):
    if isinstance(a, Q):
        return '"' + a.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'
    if isinstance(a, float):
        s = f"{a:.4f}".rstrip("0").rstrip(".")
        return s if s not in ("-0", "") else "0"
    return str(a)


def dump(node, indent=0):
    """Serialize; short lists stay on one line."""
    if not isinstance(node, list):
        return _atom(node)
    flat = "(" + " ".join(dump(x) if isinstance(x, list) else _atom(x) for x in node) + ")"
    if len(flat) <= 100 or not any(isinstance(x, list) for x in node):
        return flat
    pad = "\t" * (indent + 1)
    out = ["(" + _atom(node[0])]
    i = 1
    while i < len(node) and not isinstance(node[i], list):
        out[0] += " " + _atom(node[i])
        i += 1
    for x in node[i:]:
        out.append(pad + (dump(x, indent + 1) if isinstance(x, list) else _atom(x)))
    return "\n".join(out) + "\n" + "\t" * indent + ")"


def find(node, key):
    for x in node[1:]:
        if isinstance(x, list) and x and x[0] == key:
            return x
    return None


def findall(node, key):
    return [x for x in node[1:] if isinstance(x, list) and x and x[0] == key]
