<!-- Copyright (c) 2026 Tim Menzies, MIT License https://opensource.org/licenses/MIT -->
<a href="https://timm.fyi"><img align="right" alt="Author" src="https://img.shields.io/badge/Author-timm-dc143c?logo=readme&logoColor=white"></a><img align="right" alt="Language" src="https://img.shields.io/badge/Language-Python%203.12+-000080?logo=python&logoColor=white"><img align="right" alt="Deps" src="https://img.shields.io/badge/Deps-nuff%20(--learn)-32cd32?logo=checkmarx&logoColor=white"><a href="https://choosealicense.com/licenses/mit/"><img align="right" alt="License" src="https://img.shields.io/badge/License-MIT-32cd32?logo=open-source-initiative&logoColor=white"></a><img align="right" alt="Purpose" src="https://img.shields.io/badge/Purpose-SE·Estimation-7b68ee?logo=githubcopilot&logoColor=white"><br>

### [http://tiny.cc/xomo](http://tiny.cc/xomo)
xomo: one short file that runs COCOMO-II (effort), COQUALMO (defects)
and Boehm's risk tables (schedule/cost risk) as a Monte-Carlo over
four classic NASA/JPL case studies (flight, ground, osp, osp2). A
project is a *box* of rating ranges; sample inside it many times and
read effort, defects and risk as **distributions**, not single
guesses. The model is pure stdlib; `--learn` grows a min-variance
decision tree over the draws using [nuff](http://tiny.cc/nuff).

```bash
# install and test
git clone http://tiny.cc/xomo && cd xomo
python3 -B xomo.py             # medians (p25 p50 p75) per study
python3 -B xomo.py --learn     # decision tree: what drives good outcomes
python3 -B xomo.py --checks    # self-tests
```

**Sections:** [NAME](#name) | [SYNOPSIS](#synopsis) | [OPTIONS](#options) | [DATA](#data) | [TESTS](#tests) | [OUTPUT](#output) | [LEARN](#learn) | [CALIBRATION](#calibration) | [SEE ALSO](#see-also) | [LICENSE](#license) | [AUTHOR](#author)

**Files:** [xomo.py](http://tiny.cc/xomo#file-xomo-py) | [Makefile](http://tiny.cc/xomo#file-makefile) | [pyproject.toml](http://tiny.cc/xomo#file-pyproject-toml)

## NAME

    xomo - Monte-Carlo COCOMO-II + COQUALMO (effort, defects, risk)

## SYNOPSIS

    python3 -B xomo.py [-s N] [-n N] [-l N] [-p STUDY] [--learn] [--checks] [-h]

## OPTIONS

    -s --seed     random seed                   seed=1
    -n --n        samples/study, or --learn rows  n=1000
    -l --leaf     min rows per tree leaf         leaf=3
    -p --project  study to --learn               project=osp
       --learn    grow a decision tree (needs nuff)
       --checks   run model self-tests
    -h --help     show the docstring

## DATA

A *case study* is a dict of COCOMO driver ranges. Any driver left
unset spans its full legal range. Drivers fall in four families:

    family   members                              role
    ------   -----------------------------------  ----------------------
    sf       prec flex resl team pmat             scale factors (exponent)
    em(+)    rely data cplx ruse docu time stor   effort up as rating up
             pvol
    em(-)    acap pcap pcon aexp plex ltex tool   effort down as rating up
             site sced
    dr       aa etat pr                           defect removers

Each draw: pick an integer rating in every driver's box, then

    effort  = a * KLOC^(b + 0.01*sum SF) * prod EM        (COCOMO-II)
    defects = sum over {reqs,design,code} of
              introduced(SF,EM) * (1 - removed(dr))        (COQUALMO)
    risk    = 100 * (fired Boehm risk-table cells) / 216

## TESTS

`--checks` runs every `test_*`:

    test_positive                 effort/defects/risk finite, in range
    test_osp_riskier_than_osp2    maturing osp->osp2 cuts risk
    test_flight_bigger_than_ground tighter flight s/w costs more
    test_seed_repeats             same seed -> same draw
    test_learn_tree               nuff tree finds at least one split

## OUTPUT

    # 1000 samples/study, seed=1
                              effort               defects               risk
      study      p25     p50     p75     p25    p50    p75    p25   p50   p75
     flight      921    1971    3672    1606   3508   6939      4     6     7
     ground      558    1144    2123    1508   3471   6846      2     3     5
        osp     1743    2240    3014    3589   5511   8161     12    16    20
       osp2      237     307     386     131    205    298      3     3     4

Note osp -> osp2: process maturity (prec, pmat up) drops median effort
~7x, defects ~27x, and risk from 16 to 3 -- the "orders of magnitude"
effect, shown reproducibly.

## LEARN

`--learn` turns N random draws of one project into a table (driver
ratings -> effort/defects/risk) and grows [nuff](http://tiny.cc/nuff)'s
min-variance decision tree over it. The root split = the single factor
that most separates good from bad outcomes; follow branches to the `+`
leaf for the rating combo that minimises the blended goals.

    python3 -B xomo.py --learn -p osp2 -n 200 -l 20

       d2h    n  Effort-  Defects-  Risk-  tree
      0.51  200   324.21    228.95   3.48              <- baseline (all draws)
      0.45  148   317.55    224.21   3.12  Sced > 2
      0.37   79   260.86    194.78   3.11  |  Kloc <= 102
    + 0.31   36   231.56    170.25      3  |  |  Ltex > 3
      ...

Needs nuff: `pip install nuff`, or clone the sibling gist so
`$DOOT/nuff` is importable. `-n` sets rows, `-l` the min leaf size.

## CALIBRATION

Each draw guesses a fresh internal calibration (effort `a,b`, the EM/SF
slopes, COQUALMO m-ranges). So 1000 runs marginalize over the *space*
of plausible calibrations: a conclusion that survives is stable no
matter which calibration is "true" -- letting you decide without local
tuning data. This is the core XOMO idea (Menzies & Richardson, 2005).
Tweak the ranges in the `POLICY` block to widen or narrow that space.

## SEE ALSO

    konfig    http://tiny.cc/konfig   shared Makefile/boilerplate
    nuff      http://tiny.cc/nuff     tiny stdlib python tricks
    paper     Menzies & Richardson, "XOMO: Understanding Development
              Options for Autonomy", 20th Intl Forum on COCOMO, 2005.
              http://timmenzies.net/pdf/05xomo.pdf

## LICENSE

MIT. https://choosealicense.com/licenses/mit/

## AUTHOR

Tim Menzies, timm@ieee.org
