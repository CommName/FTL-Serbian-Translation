#!/usr/bin/env python3
"""Read-only access to FTL 1.6 ftl.dat (PKG) archives: list / extract."""
import argparse, os, struct

DEFAULT_DAT = os.path.expanduser(
    "~/.local/share/Steam/steamapps/common/FTL Faster Than Light/data/ftl.dat")


def read_index(f):
    magic, hsize, esize, count, psize = struct.unpack(">4sHHII", f.read(16))
    if magic != b"PKG\n":
        raise ValueError("not a PKG archive")
    f.seek(hsize)
    entries = [struct.unpack(">IIIII", f.read(esize)[:20]) for _ in range(count)]
    paths = f.read(psize)
    out = []
    for _h, flags, off, size, usize in entries:
        po = flags & 0xFFFFFF
        name = paths[po:paths.index(b"\0", po)].decode()
        out.append((name, off, size, usize, flags >> 24))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dat", default=DEFAULT_DAT)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    ex = sub.add_parser("extract")
    ex.add_argument("out")
    ex.add_argument("files", nargs="*", help="exact paths; empty = all")
    a = ap.parse_args()
    with open(a.dat, "rb") as f:
        idx = read_index(f)
        if a.cmd == "list":
            for name, _o, size, *_ in idx:
                print(f"{size:>10}  {name}")
            return
        want = set(a.files)
        for name, off, size, usize, fl in idx:
            if want and name not in want:
                continue
            if fl & 1 or usize != size:
                raise SystemExit(f"{name}: compressed entries not supported")
            f.seek(off)
            dst = os.path.join(a.out, name)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(dst, "wb") as o:
                o.write(f.read(size))


if __name__ == "__main__":
    main()
