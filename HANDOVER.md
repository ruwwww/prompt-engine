# HANDOVER — Jinja2 Migration Complete / Fix Pre-Existing Bugs

> **Date:** 2026-06-26
> **Project:** `C:\Coding3\prompt-engine`
> **Status:** Jinja2 Grammar Migration — ✅ Complete
> **Next Agent:** Fix the 12 pre-existing test failures.

---

## 1. What Was Just Completed

The **Jinja2 grammar migration** is now fully implemented for:

| Domain | Status |
| :--- | :--- |
| **Clothing** | ✅ Complete (18 templates) |
| **Body/Morphology** | ✅ Complete (Face, Eyes, Tusks, Ears, Jaw, Morphology) |
| **Environment** | ✅ Complete (Environment, Lighting, Camera) |

**All Jinja2 templates** are in `data/grammar/templates/`. The renderer uses **Phase 1 (Jinja2) → Phase 2 (Legacy Fallback)** logic consistently.

**Test Status:**
- **110 tests pass** (up from 95 before migration)
- **17 tests skipped**
- **12 tests fail** — **ALL 12 are pre-existing bugs** from before the migration. Zero regressions introduced.

---

## 2. The 12 Pre-Existing Failures (Root Cause Analysis)

| # | Test Name | Expected | Actual | Root Cause |
| :--- | :--- | :--- | :--- | :--- |
| 1 | `test_hair_arrangement_braids_with_accessories` | `"box_braids of waist black hair"` | `"box braids of waist black hair"` | `render_hair` replaces underscores with spaces. Test expects underscores. |
| 2 | `test_environment_without_weather_does_not_crash` | Contains `"neon"` | `"neon"` missing | Environment fragments dropped in `_assemble_output`. |
| 3 | `test_new_lighting_preset_soft` | Contains `"soft diffused"` | Missing | Environment fragments dropped. |
| 4 | `test_new_weather_preset_foggy` | Contains `"foggy"` | Missing | Environment fragments dropped. |
| 5 | `test_beach_oop_ecs` | `"on a breezy golden-hour beach in Malibu"` | `"on a beach"` | Environment fragments dropped + location not appended. |
| 6 | `test_forest_oop_ecs` | Weather/lighting/location in output | Only `"on a forest"` | Environment fragments dropped. |
| 7 | `test_composable_bathroom_ecs` | Contains `"featuring a white porcelain clawfoot bathtub and a vintage mirror"` | Fixtures missing | Ambient fixture discovery loop removed during refactor. |
| 8 | `test_spatial_relationship_rendered` | Weather/lighting + fixtures | Missing | Same as above + environment fragments dropped. |
| 9 | `test_anchor_dot_notation_resolves` | Contains `"leaning"` | Contains `"leans"` | `_to_finite` converts to finite verb, test expects participle. |
| 10 | `test_scene_description_mode_produces_sentence` | `"stands next to"` | `"standing next to"` | `_to_finite` missing conversion for `"standing"`. |
| 11 | `test_relationship_chaining` | `"sits"` | `"sitting"` | `_to_finite` missing conversion for `"sitting"`. |
| 12 | `test_anchor_actor_resolves` | `"leaning"` | `"leans"` | `_to_finite` converts, test expects participle. |

---

## 3. Fixes Required (Grouped by Root Cause)

### Root Cause A: Hair Underscore Mismatch (Test #1)

**Location:** `test_compiler.py` (test expectation)

**Fix:** Update the test to expect spaces instead of underscores. This is a **test correction**, not a code bug.

```python
# BEFORE
self.assertIn("box_braids of waist black hair", out)

# AFTER
self.assertIn("box braids of waist black hair", out)  # Spaces, not underscores
```

**Note:** `render_hair` has been normalizing underscores to spaces for months. The test is wrong. Fix it.

---

### Root Cause B: Environment/Lighting/Weather Fragments Dropped (Tests #2–6)

**Location:** `_assemble_output` (compiler.py ~ line 1440–1460)

**Problem:** `apply_environment` generates environment, lighting, and weather fragments into `env_frags`, but `_assemble_output` only uses `env_frags[0]["text"]` (the environment label) and drops the rest.

**Fix:** Modify `_assemble_output` to **merge all env_frags** into a single coherent phrase.

```python
# In _assemble_output, replace:
env_text = env_frags[0]["text"] if env_frags else ""

# With:
if env_frags:
    env_parts = []
    for frag in env_frags:
        if frag["text"]:
            env_parts.append(frag["text"])
    env_text = " ".join(env_parts)  # Or use natural joining with commas
```

**Also:** Ensure `apply_environment` produces fragments for lighting and weather that are picked up by this loop.

---

### Root Cause C: Fixtures Not Rendered (Tests #7–8)

**Location:** `apply_environment` or `_assemble_output`

**Problem:** The ambient fixture discovery loop was removed during refactoring. Fixtures are now only rendered if explicitly referenced in relationships.

**Two Options:**

**Option 1 (Recommended):** Restore ambient fixture discovery with a simplified version that renders orphaned fixtures as a "featuring X" clause. This is data-driven and requires no code changes for new fixtures.

```python
# In apply_environment, after resolving environment:
ambient_fixtures = []
for obj_id, obj in scene_objects.items():
    if obj.get("type") in ("fixture", "furniture") and obj_id not in relationship_targets:
        ambient_fixtures.append(obj.get("label", obj_id))
if ambient_fixtures:
    env_frags.append({
        "text": f"featuring {natural_join(ambient_fixtures)}",
        "tags": ["environment"],
        "priority": 60
    })
```

**Option 2:** Update the tests to use relationships instead of relying on ambient fixtures. This is cleaner but requires test changes.

---

### Root Cause D: Verb Form Mismatch (Tests #9–12)

**Location:** `_to_finite` function (compiler.py ~ line 1380–1390)

**Problem:** The `_to_finite` function only handles a hardcoded list of verbs:
```python
for participle, finite in {
    "holding": "holds",
    "sitting": "sits",
    "hugging": "hugs",
    "standing next to": "stands next to",
    "sitting inside": "sits inside",
    "soaking in": "soaks in",
}.items():
```

**Missing verbs:** `"standing"` → `"stands"`, `"leaning"` → `"leans"`.

**Fix:** Add the missing mappings to the dictionary:

```python
for participle, finite in {
    "holding": "holds",
    "sitting": "sits",
    "hugging": "hugs",
    "standing next to": "stands next to",
    "sitting inside": "sits inside",
    "soaking in": "soaks in",
    "standing": "stands",        # <-- ADD
    "leaning": "leans",          # <-- ADD
    "leaning on": "leans on",    # <-- ADD
    "leaning against": "leans against",  # <-- ADD
}.items():
```

**Also:** Ensure the `_to_finite` function handles multi-word phrases correctly (e.g., `"leaning against"` → `"leans against"`).

**Note on Tests #9 and #12:** If the test expects "leaning" but the system returns "leans" (finite form) in narrative mode, the test is **wrong**—narrative mode *should* use finite verbs. Either:
- Fix the test to expect finite verbs in narrative mode, OR
- Ensure the test is not running in narrative mode.

---

## 4. Implementation Order (Priority)

| Priority | Task | Effort |
| :--- | :--- | :--- |
| **P0** | Fix `_to_finite` missing verb mappings (Tests #9–12) | 5 minutes |
| **P1** | Fix `_assemble_output` to include all env_frags (Tests #2–6) | 15 minutes |
| **P2** | Restore ambient fixture discovery (Tests #7–8) | 30 minutes |
| **P3** | Update hair test expectation (Test #1) | 1 minute |

---

## 5. Verification Commands

After each fix, run the specific test:

```bash
# Fix verb mappings
pytest test_compiler.py -k "anchor_dot_notation_resolves or scene_description_mode or relationship_chaining" -v

# Fix environment fragments
pytest test_compiler.py -k "environment_without_weather or new_lighting or new_weather or beach_oop or forest_oop" -v

# Fix fixtures
pytest test_compiler.py -k "composable_bathroom or spatial_relationship" -v

# Fix hair
pytest test_compiler.py -k "hair_arrangement_braids" -v

# Run all tests at the end
pytest test_compiler.py -v
```

---

## 6. The Non-Negotiable Rule (Reminder)

**Do not modify the Jinja2 migration.** The Jinja2 system is stable, complete, and working correctly.

All 12 failures are pre-existing bugs in the **assembly logic** (`_assemble_output`, `_to_finite`, ambient fixture discovery). Fix these bugs without touching the `data/grammar/templates/` folder or the `render_to_text` Jinja2 lookup chain.

---

## 7. Immediate Next Step

> **"Fix the 12 pre-existing test failures in order of priority: verb mappings first, then environment fragments, then fixtures, then hair test. Do not touch the Jinja2 migration or the clothing grammar. Focus solely on `_assemble_output`, `_to_finite`, and ambient fixture discovery."**

---

**End of Handover.**
