# Evaluation protocol

Use paired runs to decide whether a skill revision is better. “Feels faster” is not evidence.

## Controls

Run baseline and candidate with the same:

- GPT-6 Astra model and reasoning effort;
- repository commit and clean worktree;
- task prompt, permissions, tools, and environment;
- timeout and retry policy.

Use a fresh thread for every run. Randomize baseline/candidate order when repeating cases.

## Score four dimensions

1. **Outcome:** requested behavior works; original reproduction passes; no known contract is broken.
2. **Process:** correct skill and route; no unrelated edits; no hidden failure suppression; appropriate permissions.
3. **Quality:** final diff survives a blinded review for correctness, security, compatibility, and maintainability.
4. **Efficiency:** elapsed time, model input/output/cached tokens when exposed, tool calls, duplicate reads, commands, and files inspected.

Passing tests are evidence, not the sole oracle. Confirm the user-visible requirement and inspect the diff.

## Fixtures

`evals/cases.jsonl` contains trigger, route, behavior, and anti-trigger cases. For a release candidate:

- run every routing case;
- run at least one real repository task per `astra-code` route;
- run `astra-repo-audit` once in report-only mode and once in edit mode on a disposable fixture;
- repeat noisy cases at least three times;
- retain prompts, traces, diffs, command logs, and grader output.

## Release gate

- All deterministic validation and unit tests pass.
- No safety boundary is weakened.
- No routing regression appears in the fixture set.
- Outcome quality is no worse than baseline.
- Any speed or token claim reports the sample, model, environment, statistic, and raw artifacts.

If the measurements are unavailable, publish the workflow change without a performance claim.
