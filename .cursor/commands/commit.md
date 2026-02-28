---
description: Create an atomic conventional commit for current changes
---

# Commit Changes

Create a new commit for all uncommitted changes in this project.

## Workflow

1. Review the current change set:

```bash
git status
git diff HEAD
git status --porcelain
```

2. Stage relevant tracked and untracked files.
3. Write an atomic commit message that reflects the intent of the change.
4. Use a conventional-style tag in the commit title, such as:
   - `feat`
   - `fix`
   - `docs`
   - `refactor`
   - `test`
   - `chore`

## Output

Return:
- Commit hash
- Final commit message
- Short summary of files included
