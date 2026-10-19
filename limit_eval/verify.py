"""One-command receipt check: python -m limit_eval.verify [--committed results] [--readme README.md]

Re-runs the scripted baseline (5 seeds) into a temp dir, then checks:
  1. results/episodes.jsonl and results/baseline.md in the repo are byte-identical to the re-run (sha256);
  2. every number the README's "Baseline results" summary quotes appears in the re-run baseline.md.
Prints one line per check and exits 0 only if all pass. No network, no keys, standard library only.
"""
import argparse, hashlib, os, re, sys, tempfile, contextlib, io

from . import run as R

FILES = ("episodes.jsonl", "baseline.md")


def sha(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def readme_numbers(readme_text):
    """The exact counts the README summary quotes: 'x/y' pairs and '[a, b]' intervals in the summary block."""
    m = re.search(r"## Baseline results.*?(?=\n## )", readme_text, re.S)
    block = m.group(0) if m else ""
    fracs = re.findall(r"\b\d+/\d+\b", block)
    ivals = re.findall(r"\[\d\.\d{3}, \d\.\d{3}\]", block)
    return fracs, ivals


def check(committed="results", readme="README.md", seeds=5, out=None):
    lines, ok = [], True
    with tempfile.TemporaryDirectory() as tmp:
        with contextlib.redirect_stdout(io.StringIO()):
            R.main(["--seeds", str(seeds), "--out", tmp])
        for name in FILES:
            a, b = os.path.join(committed, name), os.path.join(tmp, name)
            if not os.path.exists(a):
                ok = False; lines.append(f"FAIL {name}: missing from {committed}/"); continue
            same = sha(a) == sha(b)
            ok &= same
            lines.append(f"{'MATCH' if same else 'FAIL'} {name}: committed {sha(a)[:16]} vs re-run {sha(b)[:16]}")
        base = open(os.path.join(tmp, "baseline.md")).read()
        fracs, ivals = readme_numbers(open(readme).read())
        if not fracs:
            ok = False; lines.append("FAIL README: no numbers found in the 'Baseline results' section")
        missing = [x for x in fracs + ivals if x not in base]
        ok &= not missing
        lines.append(f"{'MATCH' if not missing else 'FAIL'} README summary: {len(fracs) + len(ivals) - len(missing)}/{len(fracs) + len(ivals)} quoted numbers found in re-run baseline.md"
                     + (f" (missing: {', '.join(missing)})" if missing else ""))
    lines.append("RECEIPTS REPRODUCE" if ok else "RECEIPTS DO NOT REPRODUCE")
    return ok, lines


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--committed", default="results")
    ap.add_argument("--readme", default="README.md")
    a = ap.parse_args(argv)
    ok, lines = check(a.committed, a.readme)
    print("\n".join(lines))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
