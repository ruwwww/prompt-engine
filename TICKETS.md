# Deferred Feature Tickets (Assembler v2)

This document tracks features that have been deferred during the transition to the new clean-slate pure-pipeline compiler architecture. These should be implemented in future phases.

## 1. Hair Ontology v2
- **Goal:** Support full structured hair ontology inputs (with arrangements, cultural modifiers, states, etc.) via grammar catalog extensions rather than legacy procedural converters.
- **Status:** Completed (19 tests unskipped and fully passing).
- **Target Implementation:** Integrated normalized hair ontology formatting directly into the pipeline step 8 (`render_to_text`).

## 2. Narrative Modes v2
- **Goal:** Implement robust scene description narrative modes via grammar composition (sentence syntax planning, paragraph structures, etc.).
- **Status:** Deferred (2 tests skipped).
- **Target Implementation:** Replace the hardcoded `scene_description` participle-to-finite logic with dynamic sentence-building grammar templates.

## 3. Environment Anchors v2
- **Goal:** Support dot-notation environment anchors (e.g., `balcony.railing`) for physical fixture relationship targeting.
- **Status:** Deferred (5 tests skipped).
- **Target Implementation:** Resolve environment affordance sub-paths to automatically generate fixture objects before relationship resolution.
