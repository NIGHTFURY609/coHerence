# CoHERence

Inclusive software testing playground.

Software is often designed around an assumed **default user**. Interfaces and workflows can work well for some people and create unnecessary friction or disadvantage for others.

CoHERence lets a developer put a product, prototype, or interface into a virtual testing environment and evaluate it against a diverse range of users and situations.

**Instead of asking “does this software work?” it asks:**

**Who does this software work well for, who does it work poorly for, and why?**

Source: [`docs/idea-brief.md`](docs/idea-brief.md)

## How it works

A developer provides their software, prototype, or interface.

The system creates a diverse population of virtual users with different characteristics, abilities, contexts, and **constraints**. Agents interact with the software as those users would.

It observes:

- task completion
- errors
- interaction difficulty
- time taken
- accessibility
- physical or cognitive constraints
- navigation complexity
- failure patterns
- differences in experience between user groups

Then it looks for **systematic disparities**. Example: a workflow fails much more often for users with certain physical or accessibility characteristics. The system identifies the relevant design element, explains the potential reason, and suggests how the design could be improved.

## Core concept

Unit testing for inclusive design.

Traditional tests ask whether the software behaves correctly. This system tests whether it behaves fairly and effectively across different kinds of users.

## What makes it different

The goal is not an AI that pretends to be a woman, man, elderly person, or disabled person.

It models human diversity and real-world constraints, then observes how those differences affect interaction. Gender is one possible analytical dimension; it is not a collection of stereotypes.

The broader question: **does a design assumption systematically disadvantage a particular population?**

## Docs

- [`docs/idea-brief.md`](docs/idea-brief.md) — product idea
- [`docs/arch.md`](docs/arch.md) — architecture (placeholder)
- Pipeline diagrams in `docs/` (`accessibility_testing_pipeline.svg`, `accessibility_testing_evaluation_pipeline_v2.svg`)

## Getting started

Python 3.10+. The fairness engine lives in `hydrogen/`.

Fish:

```fish
python3 -m venv .venv
source .venv/bin/activate.fish
pip install -r requirements.txt
python -m pytest
```

Bash:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m pytest
```

Any shell, no activate:

```
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest
```

## License

MIT
