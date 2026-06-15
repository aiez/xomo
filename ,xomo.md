<!-- Copyright (c) 2026 Tim Menzies, MIT License https://opensource.org/licenses/MIT -->
<a href="https://timm.fyi"><img align="right" alt="Author" src="https://img.shields.io/badge/Author-timm-dc143c?logo=readme&logoColor=white"></a><img align="right" alt="Language" src="https://img.shields.io/badge/Language-Python%203.12+-000080?logo=python&logoColor=white"><img align="right" alt="Deps" src="https://img.shields.io/badge/Deps-0-32cd32?logo=checkmarx&logoColor=white"><a href="https://choosealicense.com/licenses/mit/"><img align="right" alt="License" src="https://img.shields.io/badge/License-MIT-32cd32?logo=open-source-initiative&logoColor=white"></a><img align="right" alt="Purpose" src="https://img.shields.io/badge/Purpose-SE·Estimation-7b68ee?logo=githubcopilot&logoColor=white"><br>

### [http://tiny.cc/xomo](http://tiny.cc/xomo)
xomo: one short file that runs COCOMO-II (effort), COQUALMO (defects)
and Boehm's risk tables (schedule/cost risk) as a Monte-Carlo over
four classic NASA/JPL case studies (flight, ground, osp, osp2). A
project is a *box* of rating ranges; sample inside it many times and
read effort, defects and risk as **distributions**, not single
guesses. Pure stdlib, zero dependencies.

```bash
# install and test
git clone http://tiny.cc/xomo && cd xomo
python3 -B xomo.py            # medians (p25 p50 p75) per study
python3 -B xomo.py --checks   # self-tests
```

**Sections:** [NAME](#name) | [SYNOPSIS](#synopsis) | [OPTIONS](#options) | [DATA](#data) | [TESTS](#tests) | [OUTPUT](#output) | [CALIBRATION](#calibration) | [SEE ALSO](#see-also) | [LICENSE](#license) | [AUTHOR](#author)

**Files:** [xomo.py](#file-xomo-py) | [Makefile](#file-makefile) | [pyproject.toml](#file-pyproject-toml)

## NAME

    xomo - Monte-Carlo COCOMO-II + COQUALMO (effort, defects, risk)

## SYNOPSIS

    python3 -B xomo.py [--seed=N] [--n=N] [--checks] [-h]

## OPTIONS

    -s --seed   random seed         seed=1
    -n --n      samples per study    n=1000
       --checks run model self-tests
    -h --help   show the docstring

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

## OUTPUT

    # 1000 samples/study, seed=1. each cell = p25 p50 p75
      study                   effort               defects               risk
     flight      867    1989    3811    1551   3605   7186      4     5     7
     ground      511    1156    2174    1555   3493   7203      2     3     5
        osp     1622    2250    3117    3721   5672   8136     12    16    20
       osp2      224     309     407     132    202    298      3     3     4

Note osp -> osp2: process maturity (prec, pmat up) drops median effort
~7x, defects ~28x, and risk from 16 to 3 -- the "orders of magnitude"
effect, shown reproducibly.

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
