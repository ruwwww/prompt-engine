# Deferred Feature Tickets (Assembler v2)

This document tracks features that have been deferred during the transition to the new clean-slate pure-pipeline compiler architecture. These should be implemented in future phases.

## 1. Hair Ontology v2
- **Goal:** Support full structured hair ontology inputs (with arrangements, cultural modifiers, states, etc.) via grammar catalog extensions rather than legacy procedural converters.
- **Status:** Completed (19 tests unskipped and fully passing).
- **Target Implementation:** Integrated normalized hair ontology formatting directly into the pipeline step 8 (`render_to_text`).

## 2. Narrative Modes v2
- **Goal:** Implement robust scene description narrative modes via grammar composition (sentence syntax planning, paragraph structures, etc.).
- **Status:** Completed (unskipped and fully passing).
- **Target Implementation:** Added helper wrappers for subject capitalization, article insertion, period termination, and space-separated layout assembly.

## 3. Environment Anchors v2
- **Goal:** Support dot-notation environment anchors (e.g., `balcony.railing`) for physical fixture relationship targeting.
- **Status:** Completed (7 tests unskipped and fully passing).
- **Target Implementation:** Added parsing of dot-notation anchor targets inside `assemble()`, dynamically instantiating synthetic fixture objects using environment affordances if they match, and relaxed `object_id` requirement constraints in `apply_relationships` for single-actor relationships (e.g. `sitting`).
