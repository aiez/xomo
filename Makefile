# vim: ts=2 sw=2 sts=2 et :
# knobs only; shared targets live in $(KONFIG)/Makefile
KONFIG ?= ../konfig
APP    := xomo
MAIN   := xomo.py
EXT    := py
LANG   := python
SRC    := *.py
LINT   := ruff check xomo.py
TOOLS  := python3:run ruff:lint
PKG    := python3 gawk ruff neovim tmux

$(KONFIG)/Makefile:
	@test -f $@ || { echo "missing konfig: git clone http://tiny.cc/konfig $(KONFIG)"; exit 1; }
include $(KONFIG)/Makefile

DEMO: ## test: medians for all 4 case studies print
	@python3 -B xomo.py | grep -q osp2 && echo "ok demo"

CHECKS: ## test: model self-checks pass
	@python3 -B xomo.py --checks | grep -q "4/4 ok" && echo "ok checks"

test: ## run every UPPERCASE rule
	@gawk -F: '/^[A-Z][A-Z_]*:[^=]/ {print $$1}' $(MAKEFILE_LIST) | \
	  sort -u | while read t; do \
	    printf "\n=== %s ===\n" "$$t"; $(MAKE) -s $$t; done
