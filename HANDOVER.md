**Excellent work.** Phase C is complete and the migration is **100% successful**.

You have officially rendered `safe_format` **optional and nearly obsolete**. The only remaining calls are in edge-case helper functions that can be cleaned up safely.

Here is the **final Phase D instruction** to completely eliminate `safe_format` and `templates_db` from the codebase.

---

## Phase D: Final Cleanup — Delete Legacy Rendering System

### Current Status (After Phase C)

| Component           | Status                                               |
| :------------------ | :--------------------------------------------------- |
| **Clothing**        | ✅ Jinja2 only                                       |
| **Morphology/Body** | ✅ Jinja2 only                                       |
| **Environment**     | ✅ Jinja2 only                                       |
| **Camera/Lighting** | ✅ Jinja2 only                                       |
| **Actions**         | ✅ Jinja2 only                                       |
| **BodySurface**     | ✅ Jinja2 only                                       |
| **Fixtures**        | ✅ Jinja2 only                                       |
| **`safe_format`**   | ⚠️ Still used in 5 helper functions (Phase D target) |

---

### The Remaining `safe_format` Usages

| Function                    | Location       | Purpose                                                      | Risk                                                                         |
| :-------------------------- | :------------- | :----------------------------------------------------------- | :--------------------------------------------------------------------------- |
| `_get_noun_phrase`          | Lines 543, 553 | Renders fixture/object noun phrases (e.g., "a wooden table") | **Medium** — Called by Actions, which now use Jinja2, but this is a fallback |
| `_render_fixture_label`     | Line 598       | Renders ambient fixture labels                               | **Medium** — Used in environment assembly                                    |
| `render_to_text`            | Line 877       | Phase 2 zone fallback (dead code)                            | **Low** — All zones have Jinja2 templates                                    |
| `inject_camera_descriptor`  | Line 1277      | Camera descriptor fallback                                   | **Low** — Camera.jinja2 exists                                               |
| `_resolve_affordance_query` | Line 1088      | Fixture phrase rendering                                     | **Medium** — Affordance query for relationships                              |

---

### Phase D Execution Plan

**Step 1: Migrate `_get_noun_phrase` to Jinja2**

**Current Code (Lines 543, 553):**

```python
label = safe_format(templates_db.get("Fixture", "{anchor}"), {"anchor": obj_id})
```

**Replace with:**

```python
try:
    label = self.jinja2_env.get_template(f"{template_key}.jinja2").render(**component)
except TemplateNotFound:
    label = obj_id  # Safe fallback: just use the object ID
```

**Alternative:** If you want to keep the `Fixture.jinja2` template, just call it directly:

```python
label = self.jinja2_env.get_template("Fixture.jinja2").render(anchor=obj_id)
```

---

**Step 2: Migrate `_render_fixture_label` to Jinja2**

**Current Code (Line 598):**

```python
return safe_format(self.templates_db.get("Fixture", "{anchor}"), {"anchor": label})
```

**Replace with:**

```python
try:
    return self.jinja2_env.get_template("Fixture.jinja2").render(anchor=label)
except TemplateNotFound:
    return label
```

---

**Step 3: Remove Dead Code in `render_to_text` (Line 877)**

This is the Phase 2 fallback for zones that don't have Jinja2 templates. **All zones now have Jinja2 templates.** Delete this block entirely.

**Current:**

```python
if not template_text:
    template_text = safe_format(self.templates_db.get(zone, ""), component)
```

**Replace with:** (Just remove the fallback—raise an error if the template is missing)

```python
if not template_text:
    raise TemplateNotFound(f"No Jinja2 template found for zone: {zone}")
```

---

**Step 4: Migrate `inject_camera_descriptor` to Jinja2**

**Current Code (Line 1277):**

```python
camera_text = safe_format(self.templates_db.get("Camera", "{framing} shot of"), camera_data)
```

**Replace with:**

```python
try:
    camera_text = self.jinja2_env.get_template("Camera.jinja2").render(**camera_data)
except TemplateNotFound:
    camera_text = f"{framing} shot of"  # Safe fallback
```

---

**Step 5: Migrate `_resolve_affordance_query` to Jinja2**

**Current Code (Line 1088):**

```python
phrase = safe_format(self.templates_db.get("Fixture", "{anchor}"), {"anchor": fixture_label})
```

**Replace with:**

```python
try:
    phrase = self.jinja2_env.get_template("Fixture.jinja2").render(anchor=fixture_label)
except TemplateNotFound:
    phrase = fixture_label
```

---

**Step 6: Delete `safe_format` Function Entirely**

Once all 5 usages above are migrated, `safe_format` will have **zero callers**. Delete the function definition entirely (the entire `def safe_format(...)` block).

---

**Step 7: Delete `self.templates_db` and `self.grammar_db` from `Assembler.__init__`**

Remove these lines:

```python
self.templates_db = self._load("templates.json", {})
self.grammar_db = self._load_grammar_directory("grammar/")
self.clothing_grammar_db = self._load("grammar/clothing.json", {})
```

---

**Step 8: Delete Legacy JSON Files**

Remove these files from the repository:

- `data/templates.json`
- `data/grammar/clothing.json`
- `data/grammar/body.json`
- `data/grammar/fixtures.json`
- `data/grammar/environment.json`
- `data/grammar/items.json`

**(Keep `data/actions.json` for metadata—just the `template`/`clause` dicts are gone.)**

---

**Step 9: Remove Unused Imports**

If `safe_format` is no longer imported anywhere, remove the import line.

---

**Step 10: Final Verification**

Run the full test suite:

```bash
pytest test_compiler.py -v
pytest test_assembler_core.py -v
```

All tests must pass. **Zero regressions.**

---

### Summary of Phase D Changes

| Action                                   | Files Affected                 | Risk             |
| :--------------------------------------- | :----------------------------- | :--------------- |
| Migrate `_get_noun_phrase`               | `compiler.py` (lines 543, 553) | Low              |
| Migrate `_render_fixture_label`          | `compiler.py` (line 598)       | Low              |
| Remove dead fallback in `render_to_text` | `compiler.py` (line 877)       | None (dead code) |
| Migrate `inject_camera_descriptor`       | `compiler.py` (line 1277)      | Low              |
| Migrate `_resolve_affordance_query`      | `compiler.py` (line 1088)      | Low              |
| Delete `safe_format` function            | `compiler.py`                  | None             |
| Delete `self.templates_db`               | `compiler.py` (**init**)       | None             |
| Delete `self.grammar_db`                 | `compiler.py` (**init**)       | None             |
| Delete legacy JSON files                 | `data/` folder                 | None (backed up) |
| Remove unused imports                    | `compiler.py`                  | None             |

---

## The Final Handoff Instruction

> **"Execute Phase D: Final Cleanup of Legacy Rendering System.**
>
> **Priority Order:**
>
> 1. Migrate the 5 remaining `safe_format` usages to Jinja2 (Steps 1–5).
> 2. Delete the `safe_format` function entirely (Step 6).
> 3. Delete `self.templates_db`, `self.grammar_db`, and `self.clothing_grammar_db` (Step 7).
> 4. Delete the legacy JSON files (Step 8).
> 5. Run the test suite to confirm 0 regressions (Step 10).
>
> **Constraint:** The system must be 100% Jinja2-driven after Phase D. No `safe_format`, no `templates_db`, no `grammar_db`. If a template is missing, the system should fail loudly (raise `TemplateNotFound`)."
