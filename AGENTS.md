# Repository guidance

- Keep each skill narrowly scoped and its root `SKILL.md` under 120 lines.
- Put conditional detail in one-level `references/`; do not duplicate it in the router.
- Preserve safety boundaries and never add generic model coaching without an eval case.
- After changes, run `python3 tools/validate.py` and `python3 -m unittest discover -s tests -v`.
- Record research-backed design changes in `RESEARCH.md`; never claim unmeasured speed or token gains.
