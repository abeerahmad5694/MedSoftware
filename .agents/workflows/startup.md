---
description: 
---

# Workspace Startup Workflow

## Sequence
1. **Index:** Run `ag-refresh` to map the repository.
2. **Health Check:** Run `npm test` or equivalent to ensure the baseline is stable.
3. **Report:** Provide a brief summary of project health in the `Agent Manager` view.

## Trigger
- Activate this workflow whenever the workspace is opened or a new feature branch is created.