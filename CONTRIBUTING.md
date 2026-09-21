# Contributing

The project optimizes for useful evidence per context token, not for the number of rules.

## Change policy

- Keep skill descriptions narrow and front-load the real trigger.
- Put shared behavior in `SKILL.md` and conditional behavior in a directly linked reference.
- Prefer instructions to scripts. Add a script only when deterministic repetition is materially safer or cheaper.
- Preserve production, credential, destructive-action, and external-write boundaries.
- Add an eval case for a routing or behavioral change.
- Do not publish performance claims without a reproducible paired run.

## Checks

```bash
python3 tools/validate.py
python3 -m unittest discover -s tests -v
```

For instruction changes, also inspect the diff and run the paired protocol in [EVALUATION.md](EVALUATION.md) when practical.
