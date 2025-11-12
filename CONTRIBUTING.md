# Contributing to CodeNews

Thanks for helping improve CodeNews! This document outlines the ground rules for contributing to the project, which is distributed under the **CodeNews Personal Use License** (non-commercial). Please read it fully before opening an issue or Pull Request (PR).

## 1. Code of Conduct
- Be respectful, constructive, and inclusive.
- Report bugs with clear reproduction steps and logs.
- Avoid sharing proprietary or confidential data in issues/PRs.

## 2. License & Usage
- By contributing, you agree that your work is licensed under the CodeNews Personal Use License.
- Do not submit code or dependencies that impose commercial or conflicting terms.
- Confirm in your PR description that you understand the project cannot be used commercially without permission.

## 3. GitHub Flow
1. Fork the repository and clone your fork.
2. Create a branch from `main`: `git checkout -b feature/<short-summary>`.
3. Make focused commits with descriptive messages.
4. Push your branch and open a PR against `main`.
5. Request a review if possible; respond to feedback promptly.

## 4. Development Standards
- **Python version**: 3.11+
- **Style**: follow existing patterns; favour readability over cleverness.
- **Dependencies**: avoid heavy additions unless justified; update `requirements.txt` if needed.
- **Secrets**: never hard-code tokens or keys. Use env vars or `config.yaml` defaults.
- **Comments**: add concise explanations only where logic is non-obvious.

## 5. Testing & Validation
- Run `pytest` locally before pushing.
- If you touch Telegram, RSS, or deployment logic, describe how you tested it (unit tests, manual run, etc.).
- Add or update tests for new behaviour when feasible.

## 6. Documentation
- Update `README.md`, `QUICKSTART.md`, or `DEPLOYMENT.md` when behaviour, environment variables, or workflows change.
- Add inline docstrings for new modules or complex functions.

## 7. Pull Request Checklist
Before requesting review, ensure that:
- [ ] Tests pass locally (`pytest`).
- [ ] Lint/formatting issues are addressed (if applicable).
- [ ] Documentation reflects the change.
- [ ] Secrets are not committed.
- [ ] The PR description explains **what** changed, **why**, and how to test.
- [ ] You added a note confirming awareness of the non-commercial license.

## 8. Communication
- Use GitHub Issues for bugs/enhancements.
- Prefer small, focused PRs; large refactors should be discussed in an issue first.
- When in doubt about scope or direction, open a draft PR for early feedback.

Thanks again for contributing and keeping CodeNews community-friendly! 🙌

