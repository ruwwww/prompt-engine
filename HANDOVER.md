**Directive: Execute Phased Migration of Legacy `safe_format` Dependencies**

---

**1. Assessment Confirmation:**
The forensic audit is accepted. The assessment that `safe_format` cannot be deleted yet is correct. The plan is to execute a **3-Phase Migration**:

- **Phase A (BodySurface)** — Low effort.
- **Phase B (Fixtures)** — Low/Medium effort.
- **Phase C (Actions)** — High effort (the main blocker).
- **Phase D (Cleanup)** — Delete legacy code.

---

**2. Immediate Execution Order (Phase A & B):**

**Step 1: Migrate BodySurface (Phase A)**

- **Action:** Create `data/grammar/templates/BodySurface.jinja2`.
- **Content:** `with {% if design %}{{ design }}{% endif %}`
- **Code Change:** In `render_to_text` (around line 1421), replace the `safe_format(templates_db["BodySurface"], ...)` call with a Jinja2 lookup for `BodySurface.jinja2`.
- **Deletion:** Remove the `"BodySurface"` entry from `data/templates.json`.

**Step 2: Migrate Fixtures & Items (Phase B)**
The following entries in `templates.json` are still using the legacy path: `Fixture`, `Bathtub`, `Mirror`, `Tree`, `CoffeeCup`, `Car`.

- **Action:** For each of these entries, create a corresponding `.jinja2` file in `data/grammar/templates/`.
  - _Example:_ `Fixture.jinja2` -> `{{ anchor }}`
  - _Example:_ `CoffeeCup.jinja2` -> `{% if material %}{{ material }}{% endif %} coffee cup`
- **Code Change:** Update `_get_noun_phrase` and `_render_fixture_label` to attempt a Jinja2 lookup for the `template_key` (e.g., `Bathtub.jinja2`) **before** falling back to `templates_db`.
- **Deletion:** Remove the migrated entries (Bathtub, Mirror, Tree, CoffeeCup, Car, Fixture) from `data/templates.json`.

**Step 3: Verify Phase A & B**

- Run `pytest test_compiler.py -v`.
- The test suite must show **0 regressions**—meaning the outputs should be identical to before, but now driven by Jinja2 instead of `safe_format`.

---

**3. Preparation for Phase C (Actions Migration) — Do not execute yet, just plan.**

The Audit revealed that `actions.json` is the **single largest blocker**. Before we delete `safe_format`, we need a migration strategy for Actions.

**Your Task (Design the Action Migration Strategy):**

1.  **Inventory:** Confirm the exact list of actions in `data/actions.json` (e.g., holding, sitting, leaning_on, hugging, standing_next_to, soaking_in, etc.).
2.  **Template Analysis:** Each action has a `template` (with actor) and a `clause` (without actor) and optional `variants`.
    - _Proposal:_ We will create **two** Jinja2 templates per action. E.g., `holding.jinja2` (for the full template) and `holding_clause.jinja2` (for the actor-less clause).
    - _Alternative:_ A single Jinja2 template with an `{% if include_actor %}` switch. Choose the simplest approach.
3.  **Logic Mapping:** The current logic uses `safe_format` to replace `{actor}` and `{object}` with noun phrases, handles gender/pronouns, and applies `_to_finite` for narrative mode.
    - Your plan must ensure the Jinja2 templates receive the **already-resolved noun phrases** (e.g., `{actor}` is already "the woman" or "she") to keep the templates simple and logic-free.

**Deliverable for Phase C:**

- Produce a **detailed design document** (not code yet) outlining:
  - How the Jinja2 template lookup will work for Actions (e.g., `templates/actions/holding.jinja2`).
  - How `variants` (e.g., holding a drink vs holding a phone) will be handled (probably by having `holding_drink.jinja2` checked first, or using `if` logic inside `holding.jinja2`).
  - A proposed mapping of all 12 actions to their new Jinja2 files.

---

**Summary of Commands for the Agent:**

> **"Execute Phase A and Phase B (BodySurface and Fixtures) immediately. Fix the code, create the Jinja2 files, strip the legacy entries, and verify all tests pass.**
>
> **After that, pause and deliver the Phase C design document (Actions migration strategy). Do not write the Jinja2 templates for Actions until I approve the design."**
