# Research basis

Reviewed 2026-09-21. This is a design map, not a claim that results from different models, benchmarks, or harnesses transfer unchanged to GPT-6 Astra.

| Primary source | Relevant result | Decision in this repository |
| --- | --- | --- |
| OpenAI, [Rethinking skills and prompts for GPT-6 Astra](https://developers.openai.com/blog/rethinking-skills-and-prompts-for-gpt-6-astra) | Long descriptions, overlapping skills, unconditional pre-reading, recipe-like instructions, and obsolete ask-first/test rules can impede Astra. Completion criteria help it persist. | Two narrow skills; short router; conditional references; proportionate tests; explicit completion evidence. |
| OpenAI, [Build skills](https://learn.chatgpt.com/docs/build-skills) | Skill metadata is always visible; selected bodies load on demand; descriptions drive routing; focused skills and progressive disclosure are preferred. | Small frontmatter, one-level references, no duplicate content, structural budgets enforced in CI. |
| OpenAI, [Testing Agent Skills Systematically with Evals](https://developers.openai.com/blog/eval-skills) | Evaluate outcome, process, style, and efficiency with traces and artifacts rather than intuition. | Versioned routing cases plus a paired evaluation protocol; no unmeasured performance claims. |
| OpenAI, [Shell + Skills + Compaction](https://developers.openai.com/blog/skills-shell-tips) | Descriptions act as routing logic; negative cases reduce misfires; unused resources are cheap; deterministic invocation improves reliability. | Narrow triggers, anti-trigger evals, optional resources, and explicit `$skill-name` examples. |
| OpenAI, [Codex best practices](https://learn.chatgpt.com/guides/best-practices) | Reliability comes from relevant tests, result confirmation, and diff review. | Verification ladder and final diff inspection on implementation and debugging routes. |
| Xia et al., [Agentless](https://arxiv.org/abs/2407.01489) | A simple localization → repair → validation pipeline can be competitive and low-cost; correct localization strongly correlates with success. | Hierarchical search before edits; smallest stable patch; original reproduction first. |
| Yang et al., [SWE-agent](https://arxiv.org/abs/2405.15793) | Agent-computer interface design materially affects repository navigation, editing, and test execution. | Prefer precise native search, patch, and test tools; bound noisy output; avoid tool ceremony. |
| Zhang et al., [AutoCodeRover](https://arxiv.org/abs/2404.05427) | Program-structure-aware iterative search and test-based fault localization sharpen relevant context. | Search symbols and execution boundaries; use test evidence to narrow faults when available. |
| Zhang et al., [RepoCoder](https://arxiv.org/abs/2303.12570) | Iterative retrieval-generation outperforms one-shot repository retrieval for code completion. | Let each observation refine the next search; stop retrieving once the execution path is sufficiently explained. |
| Ouyang et al., [RepoGraph](https://arxiv.org/abs/2410.14684) | Repository-level structure can improve navigation across files and dependencies. | Trace callers, contracts, and affected boundaries only when the change is cross-cutting. |
| Jimenez et al., [SWE-bench](https://arxiv.org/abs/2310.06770) | Real issues require multi-file reasoning, execution environments, and long-context management. | Eval cases include local and cross-cutting work; the workflow scales verification with impact. |
| Chen et al., [Rethinking the Value of Agent-Generated Tests](https://arxiv.org/abs/2602.07900) | More agent-written tests did not significantly improve final outcomes in the studied SWE-bench trajectories; tests often served as observation channels. | Add tests for durable behavioral contracts, not by default; treat passing tests as evidence, not the entire definition of success. |
| Anthropic, [Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) | Context is finite and exhibits diminishing returns; agents need active curation of the most useful tokens. | Targeted reads, bounded output, no repo-wide loading, and no repeated reading of unchanged content. |
| Anthropic, [Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents) | Start with the simplest effective system; coding benefits from executable feedback, while human/system-level review remains important. | One agent-native workflow rather than a mandatory multi-agent scaffold; tests plus requested-behavior and diff review. |
| Anthropic, [Harness design for long-running application development](https://www.anthropic.com/engineering/harness-design-long-running-apps) | Long work benefits from tractable chunks, structured state, and independent evaluation. | Keep plans and checkpoints conditional on task size; do not impose them on small edits. |

## Synthesis

The shared conclusion is not “always use fewer tokens.” It is “spend tokens where they reduce uncertainty.” For routine work that means targeted search, the affected execution path, and one strong verification signal. Cross-cutting contracts justify broader context and checks. Security or irreversible operations retain explicit boundaries regardless of token cost.

## Limitations

- Published benchmark scores are not directly comparable across datasets, model versions, tools, or budgets.
- Several sources study models other than Astra; only model-agnostic findings compatible with OpenAI's Astra-specific guidance were adopted.
- Static validation in this repository checks packaging and instruction budgets, not model quality. Behavioral claims require the paired eval protocol.
