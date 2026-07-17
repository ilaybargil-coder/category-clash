# Content Curator Agent — safe operating plan

## Goal

Continuously find likely gaps and mistakes in the Category Clash question bank
without allowing a model, crawler, or scheduled job to change production data on
its own.

The curator produces review candidates. A human approves each candidate as one
of:

- a new canonical answer;
- an alias of an existing answer;
- a member of a semantic duplicate group;
- a confirmed invalid answer;
- a deferred/ambiguous candidate.

## Inputs

1. The version-controlled canonical bank and aliases.
2. Rejected production submissions, aggregated by question and normalized text.
3. Existing accepted submissions, used to find popular spellings and aliases.
4. Approved source adapters for authoritative lists, for example the Israeli
   Ministry of Education, the official Israeli municipality list, the IOC, and
   recognized professional or scientific registries.
5. An optional LLM reviewer. Its output is advisory and must cite a source.

No database password, service-role key, or other secret is written to the
repository or included in a generated report.

## Pipeline

```text
collect candidates
  -> normalize per question
  -> exact/alias collision scan
  -> typo ambiguity simulation
  -> source and category-policy checks
  -> confidence/risk classification
  -> human review queue
  -> generated data change + tests
  -> pull request
  -> CI
  -> human merge
  -> normal Render seed on deploy
```

## Safety rules

- Never write directly to Supabase from the curator.
- Never deploy, merge, or approve its own pull request.
- Never loosen fuzzy thresholds to make a missing answer pass.
- Never create a global alias. Resolution remains question-specific.
- Reject a candidate if its normalized form maps to another answer in the same
  question.
- Treat semantic groups conservatively. A subtype is not automatically the same
  answer as its parent category.
- Every internet-derived candidate stores a source URL, retrieval date, and a
  short reason.
- Existing historical answers are deactivated or renamed rather than deleted
  when a submitted-answer foreign key may reference them.

## Candidate record

```json
{
  "question": "כתבו שמות של מקצועות לימוד בבית הספר",
  "submitted_form": "מחשבת ישראל",
  "proposed_action": "NEW_CANONICAL",
  "target_canonical": "מחשבת ישראל",
  "aliases": [],
  "semantic_group": null,
  "source_url": "https://pop.education.gov.il/...",
  "reason": "Listed as an Israeli high-school field of study",
  "frequency": 12,
  "confidence": "HIGH",
  "risk_flags": []
}
```

## Scheduling options

### Free, recommended for the beta

- The game already records every submission in `submitted_answers`.
- An admin report or local command ranks rejected answers by frequency.
- Once a week, Codex and Claude can audit separate batches in separate
  worktrees and create review-only pull requests.
- No paid model API or always-on worker is required.

### Automated later

A scheduled GitHub Action can run deterministic audits and open/update a report.
Adding an LLM API to that action is optional and may cost money. Even when an
LLM is enabled, it may only prepare a draft pull request.

## Parallel-agent ownership

- `claude/question-bank-audit`: corrections and resolver/admin proposals.
- `codex/comprehensive-question-audit`: sourced content expansion and curator
  tooling.
- Each agent uses its own worktree. Changes are reviewed and merged one branch
  at a time; production deploys only from `main`.

## Implementation milestones

1. Add a deterministic static audit command for counts, collisions, risky short
   aliases, singleton semantic groups, and source coverage.
2. ✅ Add a privacy-safe rejected-answer aggregation command:
   `python -m scripts.report_rejected_answers --min-count 2 --limit 100`.
   A review-decision table/API remains for the admin milestone.
3. Add the admin review queue.
4. Generate data changes from approved candidates and require CI.
5. Optionally schedule the static audit and draft-report generation.
