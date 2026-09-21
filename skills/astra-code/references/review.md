# Review code

## Workflow

1. Establish the review target and base. Inspect the diff summary before full patches.
2. Rank files by behavioral risk: trust boundaries, persistence, concurrency, public APIs, migrations, configuration, and error handling first.
3. Trace only changed execution paths and the callers or tests needed to validate a suspected issue.
4. Confirm each finding against repository behavior. Do not report a theoretical concern without a concrete failure mode.
5. Check whether tests cover the changed contract, not merely changed lines.
6. For shared contracts or new functionality, check integration beyond the diff:
   unchanged consumers, registrations, generated clients, config, permissions and
   compatibility. Use the integration reference linked from SKILL.md when relevant.

## Findings

Order findings by severity. For each finding include:

- concise impact;
- concrete trigger or failure scenario;
- exact file and line or symbol;
- smallest credible correction direction.

Prioritize correctness, security, data loss, compatibility, concurrency, and missing behavioral coverage. Omit style-only observations unless they conceal a real defect. If no material findings remain, say so and name any verification gap.
