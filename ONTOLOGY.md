# Unified Ontology (The "World Model")

## 1. The 8 Entity Classes (Mutually Exclusive)
| Class | Definition | Attributes | Output Field |
| :--- | :--- | :--- | :--- |
| **Subject** | Main character(s); "figures" | Build, Height, Skin Tone, Face Shape, Hair, Age | Subject |
| **Attire** | Wearable items on Subjects | Garment, Color, Material, Fit, Pattern, Brand | Clothing |
| **Action** | Subject behavior or interaction | Type, Target (Subject/Fixture/Object), Manner, Gaze | Action |
| **Fixture** | Structural, anchored stage elements | Label, Details, Spatial Role (Boundary/Surface/Anchor) | Action (if targeted) |
| **Object** | Inert, moveable, non-structural props | Label, Details, Color, Material | Objects |
| **Bg Element** | Passive non-interactable filler | Label, Spatial Context | Environment |
| **Atmosphere** | Global ambient properties | Ground, Envelope (lighting), Vista, Background | Env / Lighting |
| **Camera** | Perspective and framing | Framing, Angle, Depth of Field | Camera |

## 2. The Relationship Ontology (Entity Connections)
| Relationship Type | Actors (Source → Target) | Example / Semantic Rule |
| :--- | :--- | :--- |
| **Holding** | Subject → Object | Source holds Target (must be held to be active in Action/Objects) |
| **Leaning On** | Subject → Fixture | Source leans against Target |
| **Sitting On/At** | Subject → Fixture | Source sits on/at Target |
| **Framing** | Fixture → Subject(s) | Target framed/surrounded by Source |
| **Kneeling Before** | Subject → Subject | Source kneels facing Target |
| **Looking At** | Subject → Subject/Fixture/Camera | Source's gaze targets Target |
| **Standing Next To**| Subject → Fixture/Subject | Source stands adjacent to Target |

## 3. Linguistic Mapping
| Ontological Class | Jinja2 Template | Output Field |
| :--- | :--- | :--- |
| **Subject** | `Subject.jinja2` | Subject |
| **Attire** | `UpperBody.jinja2`, `LowerBody.jinja2`, `Attire.jinja2` | Clothing |
| **Action** | `holding.jinja2`, `leaning_on.jinja2`, `pose.jinja2`, etc. | Action |
| **Fixture** | `Fixture.jinja2` | Action (when targeted by an Action) |
| **Object** | `Object.jinja2` | Objects |
| **Bg Element / Atmosphere** | `Environment.jinja2` | Environment |
| **Atmosphere (Envelope)** | `Lighting.jinja2` | Lighting |
| **Camera** | `Camera.jinja2` | Camera |
| **Style / Render Profile** | `Profile.jinja2` | Style Details |

## 4. The Golden Rules of Entity Interaction
1. **Camera Framing Visibility Gate**: Any zone/element is rendered only if visible under the active `Camera` profile and not occluded by a Subject's `Action` / pose.
2. **Override Priority Order**: User scene overrides (`scene["objects"]`) always win: User Scene Values > Attire Slot Settings > Subject Preset Defaults.
3. **Eager Database Lookups**: All schema definitions, templates, and entity defaults (e.g., in `data/`) are loaded eagerly during compiler instantiation.
4. **Interaction Exclusion**: Only a `Subject` can initiate `Action` relationships; `Objects` and `Fixtures` are passive targets.
5. **No Placeholders / Strict Compilation**: When `strict=True` is active, compilation fails with `ValueError` on undefined templates or missing target actors/objects.
6. **Data-Driven Templates**: Output language format is controlled entirely by `templates.json` and mapping profiles, never hardcoded in logic.
7. **Spatial Coherence**: A Subject cannot interact with/lean/sit on a Fixture that is filtered out of the current Camera profile.
