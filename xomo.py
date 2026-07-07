#!/usr/bin/env python3 -B
"""
xomo.py, Monte-Carlo COCOMO-II + COQUALMO over 4 case studies (cli)
(c) 2026, Tim Menzies <timm@ieee.org>, MIT license

Each project is a box of rating ranges (uncertainty). Sample inside
that box many times; each draw yields an effort (COCOMO-II), a defect
count (COQUALMO), and a schedule/cost risk index (Boehm risk tables).
The spread of medians shows what is, and is not, settled about a job.

Split on purpose: POLICY = tweakable domain tables (drivers, bounds,
defect signs, calibration ranges, risk tables, case studies).
MECHANISM = generic engine that reads policy, hard-codes no numbers.

Options:
 -s --seed     random seed      seed=1
 -n --n        samples/study or --learn rows  n=1000
 -l --leaf     min rows per tree leaf         leaf=3
 -p --project  study to --learn             project=osp

eg: python3 xomo.py                       # medians: flight ground osp osp2
    python3 xomo.py --learn -p osp2 -n 128 # nuff tree over 128 draws
    python3 xomo.py --checks               # self-tests

needs nuff (the shared learner lib): pip install nuff, or clone the
sibling gist (http://tiny.cc/nuff) so $DOOT/nuff is importable.
"""
import os, re, sys, random, statistics
from random import uniform
from types import SimpleNamespace as o
try:                          # nuff = shared learner lib (pip install nuff)
  from nuff import Data, tree, treeShow
except ImportError:           # else the sibling gist under $DOOT (gists root)
  sys.path.append(os.path.join(os.environ.get("DOOT") or
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "nuff"))
  try: from nuff import Data, tree, treeShow
  except ImportError: Data = tree = treeShow = None  # only --learn needs nuff

# ===== POLICY: business knowledge -- tweak freely ==============

# One row per COCOMO driver:  name  kind  lo-hi  defect-sign
#   kind  sf=scale factor  emp/emn=effort mult (+/- slope)  dr=defect remover
#   sign  +=more defects  -=fewer  .=none  ~=none in reqs, fewer after
DRIVERS = """
  prec sf  1-5 -    flex sf  1-5 .    resl sf  1-5 -
  team sf  1-5 -    pmat sf  1-5 -
  rely emp 1-5 -    data emp 2-5 +    cplx emp 1-6 +
  ruse emp 2-6 +    docu emp 1-5 -    time emp 3-6 +
  stor emp 3-6 +    pvol emp 2-5 +
  acap emn 1-5 -    pcap emn 1-5 ~    pcon emn 1-5 -
  aexp emn 1-5 -    plex emn 1-5 -    ltex emn 1-5 -
  tool emn 1-5 -    site emn 1-6 -    sced emn 1-5 -
  aa   dr  1-6 .    etat dr  1-6 .    pr   dr  1-6 .
"""

# COCOMO-II effort calibration RANGES, sampled fresh per draw. The
# point of XOMO: each run guesses a different internal calibration, so
# 1000 runs marginalize over the space of plausible calibrations --
# conclusions that survive are stable without local tuning data.
EFFORT = o(a  =(2.25, 3.25),    # linear tuning      (paper Fig 2)
           bhi=1.1, blo=0.9,    # exponent base: b falls as a rises
           emp=( 0.073,  0.21), # +slope effort mult, per rating step
           emn=(-0.178, -0.078),# -slope effort mult
           sf =( 1.014,  1.6))  # scale-factor weight

# COQUALMO: phase -> (defects/KLOC base, intro+ m, intro- m, removal m)
PHASES = dict(
  reqs  =(10, (0.0166, 0.38 ), (-0.215, -0.035), (0.0, 0.14 )),
  design=(20, (0.0066, 0.145), (-0.325, -0.050), (0.0, 0.156)),
  code  =(30, (0.0066, 0.145), (-0.290, -0.050), (0.1, 0.176)))

# Boehm risk tables, laid out vertical so the nonzero "corner" shows.
# A cell [worse-of-a][worse-of-b] = risk points; '.' = no risk.
def grid(s):
  "Read a 6x6 risk table: '.'->0, digit->points."
  return [[0 if c == "." else int(c) for c in row.split()]
          for row in s.strip().splitlines()]

ne = grid("""
  . . . 1 2 4
  . . . . 1 2
  . . . . . 1
  . . . . . .
  . . . . . .
  . . . . . .""")
ne86 = grid("""
  . . 1 2 4 8
  . . . 1 2 4
  . . . . 1 2
  . . . . . 1
  . . . . . .
  . . . . . .""")
nw = grid("""
  4 2 1 . . .
  2 1 . . . .
  1 . . . . .
  . . . . . .
  . . . . . .
  . . . . . .""")
nw8 = grid("""
  8 4 2 1 . .
  4 2 1 . . .
  2 1 . . . .
  1 . . . . .
  . . . . . .
  . . . . . .""")
sw = grid("""
  . . . . . .
  1 . . . . .
  2 1 . . . .
  4 2 1 . . .
  . . . . . .
  . . . . . .""")
sw8 = grid("""
  . . . . . .
  1 . . . . .
  2 1 . . . .
  4 2 1 . . .
  8 4 2 1 . .
  . . . . . .""")
sw26 = grid("""
  . . . . . .
  . . . . . .
  1 . . . . .
  2 1 . . . .
  4 2 1 . . .
  . . . . . .""")
sw86 = grid("""
  . . . . . .
  1 . . . . .
  2 1 . . . .
  4 2 1 . . .
  8 4 2 1 . .
  . . . . . .""")

# which driver-pairs fire which table
RISK = dict(
  ltex=dict(pcap=nw8), pvol=dict(plex=sw),
  pmat=dict(acap=nw, pcap=sw86), ruse=dict(aexp=sw86, ltex=sw86),
  stor=dict(acap=sw86, pcap=sw86),
  cplx=dict(acap=sw86, pcap=sw86, tool=sw86),
  rely=dict(acap=sw8, pcap=sw8, pmat=sw8),
  team=dict(aexp=nw, sced=nw, site=nw),
  time=dict(acap=sw86, pcap=sw86, tool=sw26),
  tool=dict(acap=nw, pcap=nw, pmat=nw),
  sced=dict(cplx=ne86, time=ne86, pcap=nw8, aexp=nw8, acap=nw8,
            plex=nw8, ltex=nw, pmat=nw, rely=ne, pvol=ne, tool=nw))

# the 4 case studies (rating ranges; absent driver spans full bounds)
CASE = dict(
  flight = dict(kloc=(7,418),  pmat=(2,3), rely=(3,5), data=(2,3),
    cplx=(3,6), time=(3,4), stor=(3,4), acap=(3,5), aexp=(2,5),
    pcap=(3,5), plex=(1,4), ltex=(1,4), tool=(2,2), sced=(3,3)),
  ground = dict(kloc=(11,392), pmat=(2,3), rely=(1,4), data=(2,3),
    cplx=(1,4), time=(3,4), stor=(3,4), acap=(3,5), aexp=(2,5),
    pcap=(3,5), plex=(1,4), ltex=(1,4), tool=(2,2), sced=(3,3)),
  osp    = dict(kloc=(75,125), prec=(1,2), flex=(2,5), resl=(1,3),
    team=(2,3), pmat=(1,4), stor=(3,5), ruse=(2,4), docu=(2,4),
    cplx=(5,6), data=(3,3), pvol=(2,2), rely=(5,5), acap=(2,3),
    pcon=(2,3), aexp=(2,3), ltex=(2,4), tool=(2,3), sced=(1,3),
    pcap=(3,3), plex=(3,3), site=(3,3)),
  osp2   = dict(kloc=(75,125), prec=(3,5), pmat=(4,5), flex=(3,3),
    resl=(4,4), team=(3,3), docu=(3,4), ltex=(2,5), sced=(2,4),
    time=(3,3), stor=(3,3), data=(4,4), pvol=(3,3), ruse=(4,4),
    rely=(5,5), cplx=(4,4), acap=(4,4), pcap=(3,3), pcon=(3,3),
    aexp=(4,4), plex=(4,4), tool=(5,5), site=(6,6)))

# ===== MECHANISM: generic engine -- reads policy, no numbers ===

# parse DRIVERS into the lookups the engine uses
KIND, BND, SIGN = {}, {}, {}
def _load(table):
  toks = table.split()
  for i in range(0, len(toks), 4):
    name, kind, rng, sign = toks[i:i+4]
    lo, hi = map(int, rng.split("-"))
    KIND[name], BND[name], SIGN[name] = kind, (lo, hi), sign
_load(DRIVERS)

def project(case):
  "Fill every driver with a (lo,hi) box: case value, else default."
  box = {n: case.get(n, BND[n]) for n in KIND}
  return o(kloc=case["kloc"], box=box)

def sample(proj):
  "One draw: integer rating per driver + a real kloc."
  z = {n: round(uniform(lo, hi)) for n, (lo, hi) in proj.box.items()}
  return z, uniform(*proj.kloc)

def effort(z, kloc):
  "COCOMO-II: a * KLOC^(b + .01*sum SF) * prod EM."
  lo, hi = EFFORT.a
  a = uniform(lo, hi)
  b = EFFORT.bhi + (EFFORT.blo-EFFORT.bhi) * (a-lo)/(hi-lo)  # b depends on a
  prod, ssum = 1.0, 0.0
  for n, kind in KIND.items():
    if   kind == "emp": prod *= 1 + (z[n]-3) * uniform(*EFFORT.emp)
    elif kind == "emn": prod *= 1 + (z[n]-3) * uniform(*EFFORT.emn)
    elif kind == "sf":  ssum += (6 - z[n])   * uniform(*EFFORT.sf)
  return a * kloc ** (b + 0.01*ssum) * prod

def intro1(name, z, phase, pos, neg):
  "How one driver scales introduced defects (1.0 = no effect)."
  s = SIGN[name]
  if s == "+": return uniform(*pos) * (z-3) + 1
  if s == "-" or (s == "~" and phase != "reqs"):
    return uniform(*neg) * (z-3) + 1
  return 1.0

def defects(z, kloc):
  "COQUALMO: sum over phases of introduced * (1 - removed)."
  total = 0.0
  for phase, (base, pos, neg, rem) in PHASES.items():
    intro = base * kloc
    for n, kind in KIND.items():
      if kind in ("sf", "emp", "emn"):
        intro *= intro1(n, z[n], phase, pos, neg)
    kept = 1.0
    for n, kind in KIND.items():
      if kind == "dr": kept *= 1 - uniform(*rem) * (z[n] - 1)
    total += intro * kept
  return total

def risk(z):
  "Sum of fired risk cells, scaled to a 0..100 index."
  hits = sum(RISK[a][b][z[a]-1][z[b]-1]
             for a in RISK for b in RISK[a])
  return 100 * hits / 216

def run(proj):
  z, kloc = sample(proj)
  return o(effort=effort(z, kloc), defects=defects(z, kloc), risk=risk(z))

# ## report -----------------------------------------------------
def quart(xs):
  xs = sorted(xs); n = len(xs)
  return xs[n//4], xs[n//2], xs[3*n//4]

def med(xs): return statistics.median(xs)

def report(the):
  print(f"# {the.n} samples/study, seed={the.seed}")
  lmh = lambda w: "%*s %*s %*s" % (w, "p25", w, "p50", w, "p75")
  print(f"{'':>7}  {'effort':>23}  {'defects':>20}  {'risk':>17}")
  print(f"{'study':>7}  {lmh(7)}  {lmh(6)}  {lmh(5)}")
  for name in "flight ground osp osp2".split():
    random.seed(the.seed)
    rows = [run(project(CASE[name])) for _ in range(the.n)]
    e = "%7.0f %7.0f %7.0f" % quart([r.effort  for r in rows])
    d = "%6.0f %6.0f %6.0f" % quart([r.defects for r in rows])
    k = "%5.0f %5.0f %5.0f" % quart([r.risk    for r in rows])
    print(f"{name:>7}  {e}  {d}  {k}")

# ## learn: nuff's min-variance tree over random draws ----------
def table(proj, n=128):
  "n random draws as a nuff Data: ratings + kloc -> effort/defects/risk."
  head = [d.capitalize() for d in KIND] + \
         ["Kloc", "Effort-", "Defects-", "Risk-"]   # -=minimise goal
  rows = []
  for _ in range(n):
    z, kloc = sample(proj)
    rows.append(tuple([z[d] for d in KIND] + [round(kloc),
                 round(effort(z, kloc)), round(defects(z, kloc)),
                 round(risk(z))]))   # tuple: nuff keys row caches
  return Data([head] + rows)

def coachReport(the):
  "Learn a min-variance tree (nuff) over -n random draws of a project."
  if not Data: sys.exit("xomo: --learn needs nuff (see INSTALL in -h)")
  random.seed(the.seed)
  data = table(project(CASE[the.project]), the.n)
  print(f"# {the.project}: nuff tree over {the.n} random draws. leaf disty"
        " blends effort/defects/risk (lower=better); +best -worst leaf.")
  treeShow(data, tree(data, leaf=the.leaf))

# ## checks (run via --checks) ----------------------------------
def test_positive():
  "effort, defects, risk are all non-negative and finite."
  random.seed(1); proj = project(CASE["ground"])
  rows = [run(proj) for _ in range(200)]
  assert all(r.effort > 0 and r.defects >= 0 and 0 <= r.risk <= 100
             for r in rows)

def test_osp_riskier_than_osp2():
  "Literature claim: maturing osp->osp2 cuts risk."
  random.seed(1)
  r1 = med([run(project(CASE["osp"])).risk  for _ in range(400)])
  r2 = med([run(project(CASE["osp2"])).risk for _ in range(400)])
  assert r1 > r2, (r1, r2)

def test_flight_bigger_than_ground():
  "Flight software (tighter constraints) costs more than ground."
  random.seed(1)
  f = med([run(project(CASE["flight"])).effort for _ in range(400)])
  g = med([run(project(CASE["ground"])).effort for _ in range(400)])
  assert f > g, (f, g)

def test_seed_repeats():
  "Same seed -> same draw."
  random.seed(42); a = run(project(CASE["osp"])).effort
  random.seed(42); b = run(project(CASE["osp"])).effort
  assert a == b

def test_learn_tree():
  "nuff tree over draws finds at least one split (skip sans nuff)."
  if not Data: return
  random.seed(1)
  assert tree(table(project(CASE["osp"]))).at is not None

# ## lib + cli --------------------------------------------------
def settings(s):
  "Parse every var=val pair in a string into an o (ints coerced)."
  f = lambda v: int(v) if re.fullmatch(r"-?\d+", v) else v
  return o(**{k: f(v) for k, v in re.findall(r"(\w+)=(\S+)", s)})

def main(the, g):
  argv = sys.argv[1:]
  # accept -n N / --n N / --n=N (int), -p NAME / --project=NAME (str),
  # or a bare study name (osp, osp2, ...). same flags for seed.
  ints = {"-n": "n", "--n": "n", "-s": "seed", "--seed": "seed",
          "-l": "leaf", "--leaf": "leaf"}
  i = 0
  while i < len(argv):
    a = argv[i]
    if a in CASE: the.project = a
    elif "=" in a:
      k, v = a.lstrip("-").split("=")
      if   k == "project":              the.project = v
      elif k in ("n", "seed", "leaf"):  setattr(the, k, int(v))
    elif a in ("-p", "--project") and i+1 < len(argv):
      the.project = argv[i+1]; i += 1
    elif a in ints and i+1 < len(argv):
      setattr(the, ints[a], int(argv[i+1])); i += 1
    i += 1
  if "-h" in argv or "--help" in argv: return print((__doc__ or "").strip())
  if "--checks" in argv:
    tests = {k: v for k, v in g.items() if k.startswith("test_")}
    ok = 0
    for name, fn in tests.items():
      try: fn(); ok += 1; print("PASS", name)
      except Exception as e: print("FAIL", name, e)
    return print(f"# {ok}/{len(tests)} ok")
  if "--learn" in argv: return coachReport(the)
  report(the)

the = settings(__doc__)
if __name__ == "__main__":
  main(the, globals())
