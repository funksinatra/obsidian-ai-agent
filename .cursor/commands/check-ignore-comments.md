---
description: Audit noqa and type ignore suppressions with recommendations
---

# Check Ignore Comments

Find all suppression comments in the codebase and evaluate whether they should be removed, justified, or refactored.

## Scope

Search for:
- `# noqa`
- `# type: ignore`
- `# pyright: ignore`

## Analysis Requirements

For each suppression found:

1. Explain why it exists.
2. Propose at least two options:
   - effort (`Low`/`Medium`/`High`)
   - breaking change risk (`Yes`/`No`)
   - impact
3. Document tradeoffs.
4. Provide a recommendation (`Remove`, `Keep`, or `Refactor`) with justification.

## Report Output

Create a markdown report:

` .agents/reports/ignore-comments-report-{YYYY-MM-DD}.md `

If `.agents/reports` does not exist, create it first.

Use this section template for each finding:

```md
## {file path}:{line}

**Suppression:**
`{exact comment}`

**Why it exists:**
{explanation}

**Options to resolve:**
1. {Option 1}
   - Effort: {Low|Medium|High}
   - Breaking: {Yes|No}
   - Impact: {details}
2. {Option 2}
   - Effort: {Low|Medium|High}
   - Breaking: {Yes|No}
   - Impact: {details}

**Tradeoffs:**
- {tradeoff 1}
- {tradeoff 2}

**Recommendation:** {Remove|Keep|Refactor}
{justification}
```
