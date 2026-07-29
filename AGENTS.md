# Repository Guidelines

## Project Structure & Module Organization

- `dashboard/` contains the Vue 3 + TypeScript frontend. Keep components in
  `src/components/`, shared chart/data logic in `src/composables/` and
  `src/utils/`, and static packet fixtures in `public/data/`.
- `services/` builds daily packets: `data/` derives metrics,
  `evidence/` constrains stage evidence, and `ai/` builds and validates AI
  explanations.
- `tests/acceptance/` holds pytest contracts and browser acceptance coverage;
  `tests/fixtures/` contains stable input scenarios.
- `scripts/` contains maintenance and verification entry points. `specs/`
  records versioned requirements and acceptance evidence. Treat
  `prototype-*/` as local research, not production code.

## Build, Test, and Development Commands

Run commands from the repository root unless noted:

```powershell
cd dashboard; npm install; npm run dev       # local Vite server
cd dashboard; npm run build                  # vue-tsc + production build
python -m pytest -q tests/acceptance         # Python contracts
python tests/acceptance/run_acceptance.py    # build, contracts, Playwright checks
python services/run_daily.py --mock-ai       # rebuild packet with deterministic AI text
```

Use `--mock-ai` for repeatable local verification only; it does not validate a
real model call.

## Coding Style and Naming

Use four spaces in Python and two spaces in Vue/TypeScript. TypeScript is
strict: avoid `any` and preserve explicit packet types. Use `snake_case` for Python functions/files and
`PascalCase.vue` for components. Preserve canonical indicator IDs and packet
field names; do not casually rename data-contract fields. No formatter or
linter is configured, so match nearby code and let `npm run build` catch
frontend type errors.

## Testing Guidelines

Name Python tests `test_*.py` and test functions `test_*`. Add or update
fixtures when changing packet shape, evidence rules, thresholds, fallback
behavior, or AI validation. For visual changes, run the full acceptance script
and retain relevant screenshots under the existing review-evidence workflow.
Never mark a real-AI or deployment check as passed based on mock output.

## Commit and Pull Request Guidelines

Follow the existing concise convention: `feat: …`, `fix: …`, `docs: …`,
or `chore(data): …`. Keep commits focused. Before committing, inspect staged
files; do not include `dashboard/node_modules/`, `dashboard/dist/`, caches,
prototypes, credentials, or unrelated research. PRs should state the user
impact, affected packet/schema behavior, tests run, and screenshots for UI
changes.

## Product and Safety Constraints

This is a public research dashboard, not trading advice. AI may only choose
from machine-generated `allowed_stages`; it must not alter thresholds or give
price, position, leverage, or timing advice. Keep version maps, release notes,
and data licensing decisions in `specs/`.
