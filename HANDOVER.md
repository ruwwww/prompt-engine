# Handover Task List: Prompt Engine Enhancement

This task list tracks the implementation plan and status for adding Social Groups, Possession, mixed Render Styles, Camera Focus, and Narrative Mode improvements to the V2 Prompt Compiler.

## Status Summary

All features have been successfully implemented and verified. All 340 active tests (and 57 skipped ones) in the test suite pass cleanly with zero regressions.

---

## 1. Schema & Data Model Updates
- [x] Support `groups` field in scene JSON to define Social Groups (e.g., `couple`, `family`, `team`).
- [x] Support `owner` field on Objects and Fixtures to define Possession.
- [x] Support `render_style` on subjects (`photorealistic`, `stylized_3d`, etc.).
- [x] Support `focus` on Camera (`subjects`, `background`, etc.).

## 2. Compiler Pipeline Updates (`compiler.py`)
- [x] **Group Resolver**: Check for `groups` in scene JSON and override subject phrases (e.g., "A stylish couple" instead of "A man and a woman").
- [x] **Possession Resolver**: Map owned objects to their owners' possessive pronouns (`his`, `her`, `their`) or absolute possessive forms (`hers`, `his`).
- [x] **Narrative Mode Integration**: Call `_to_finite` to convert relationship action clauses into finite verb forms when `narrative_mode == "scene_description"` in both single-actor and multi-actor flows.
- [x] **Focus Rendering**: Pass `focus` parameter to camera descriptors.

## 3. Formatting & Grammar Refinement (`output_formatter.py`)
- [x] **Environment Capitalization**: Capitalize environment labels directly to preserve case assertions like `"Soft sandy shore"`, `"Sandy shore"`, and `"Forest floor"`.
- [x] **Ambient Fixture Deduplication**: Prevent ambient fixture descriptions from overwriting the base environment label.
- [x] **Verb Chaining**: In `scene_description` narrative mode, sort action clauses by `chain_order` and only convert the first verb to its finite form, leaving subsequent ones participial (e.g., `"sits inside a blue car holding..."`).
- [x] **Style & Composition Suffixes**: Apply composition suffixes (like `", shot in cinematic style"`) and render the style details overlays.
- [x] **Headwear as Accessory**: Relocate native `Headwear` to accessory lists to prefix with `"wearing"`, adding article resolution for singular items (e.g. `"wearing a black baseball cap"`).

## 4. Verification & Regression Testing
- [x] Add and execute tests for mixed render styles, camera focus, possession, and groups.
- [x] Verify using the romantic proposal stress test and multi-actor stress tests.
- [x] Run full verification suite (`pytest`) to ensure 100% success rate.
