# GitHub Copilot Repository Guidance

This repository is configured for GitHub Copilot coding agent using layered guidance files.

## Guidance hierarchy

1. `.github/copilot-instructions.md` (repository-wide baseline)
2. `.github/instructions/**/*.instructions.md` (path-specific enforcement)
3. `.github/skills/**/SKILL.md` (specialized implementation workflows)

## Available guidance

- `copilot-instructions.md`: Global backend standards and implementation constraints.
- `instructions/ats-backend-enforcement.instructions.md`: API envelope, router placement, and exception-handling enforcement for backend files.
- `skills/ai-ats-backend-implementation/SKILL.md`: ATS backend implementation workflow.
- `skills/ai-ats-backend-implementation/assets/response-envelope-dto.template.py`: Response envelope DTO template.

## Best-practice task authoring

When assigning issues to Copilot coding agent, include:
- A clear problem statement
- Acceptance criteria
- Known target files (if applicable)
- Expected validation steps (tests/lint/build)

If requirements are not captured in repository guidance, Copilot should ask clarifying questions before implementation.
