# Architectural Specification: Environment, Fixtures, and Spatial Interactions

> **Version:** 1.1 (Updated)
> **Status:** Locked for Implementation
> **Scope:** Defines the definitive ontological boundary between "Atmosphere" (ambient description) and "Fixtures" (interactable entities) within the Prompt Engine, mapped to the **Eight-Field Labeled Output Format**.

---

## 1. Core Principle (The Boundary)

**The Environment is NOT a monolithic block.** It is a layered stage.

A subject exists _within_ an atmospheric envelope (lighting, weather, ground texture) but _interacts with_ physical props (walls, chairs, arches).

**The Golden Rule:**

- If a subject **can touch, hold, sit on, lean against, or be framed by** an element, it is a **Fixture (Entity)**.
- If an element **cannot be touched** (lighting, distant vista, ambient weather), it is **Atmosphere (String)**.

---

## 2. The Three-Layer Ontology

The system recognizes exactly three distinct classes of spatial data.

### Layer 1: The Atmospheric Envelope (Flat Catalog)

_Purpose:_ Sets the global mood, ground, and distant background.

- **Storage:** `data/primitives/environments.json`
- **Data Type:** Flat JSON strings.
- **Keys:**
  - `ground`: The immediate surface the subject stands on.
  - `envelope`: Lighting, weather, and air quality.
  - `vista`: The distant background view.
  - `background` _(Optional)_: Non-interactive elements (e.g., "pedestrians walking in the distance").

**Schema Example:**

```json
"romantic_beach": {
  "ground": "soft sandy shore",
  "envelope": "romantic golden sunset lighting",
  "vista": "gentle ocean waves in the distance",
  "background": "with seabirds gliding overhead"
}
```

**Rule:** These strings are **non-targetable**. You cannot write a relationship targeting "golden sunset lighting."

---

### Layer 2: Physical Props / Fixtures (Targetable Entities)

_Purpose:_ Objects that the subject can interact with. These are the "furniture" of the scene.

- **Storage:** Explicitly defined in the user's `scene.json` under `"objects"`.
- **Fields:**
  - `type`: Must be `"fixture"`.
  - `label`: The noun phrase (e.g., "whitewashed stone wall").
  - `details`: Decorative or descriptive extras (e.g., "covered in peeling paint and graffiti").

**Schema Example:**

```json
"wall_1": {
  "type": "fixture",
  "label": "whitewashed stone wall",
  "details": "covered in peeling paint and graffiti"
}
```

**Rule:** Fixtures are **targetable**. A Subject can lean on `wall_1`.

---

### Layer 3: Spatial Interactions (Relationships)

_Purpose:_ Defines the physical connection between a Subject and a Fixture.

- **Storage:** `scene.json` under `"relationships"`.
- **Supported Types:** `leaning_on`, `sitting_on`, `holding`, `framing` (see below).

**Special Case: The `framing` Relationship**
This is a multi-actor relationship where a Fixture visually frames one or more Subjects.

- **Roles:** `object` (the fixture) and `subjects` (an array of one or more actors).

**Schema Example:**

```json
{
  "type": "framing",
  "object": "rose_arch_1",
  "subjects": ["man_1", "woman_1"]
}
```

---

## 3. The Eight-Field Labeled Output Format

The system produces a **structured, labeled output** with exactly eight fields:

```
[Summary Sentence]

Subject: [Detailed subject description]
Clothing: [Detailed clothing description]
Action: [Detailed action/pose description]
Environment: [Detailed environment description]
Lighting: [Detailed lighting description]
Camera: [Detailed camera description]
Style Details: [Detailed style description]
```

### Mapping: Environment Ontology → Labeled Fields

| Labeled Field     | Source                                                             | Content                                                                   |
| :---------------- | :----------------------------------------------------------------- | :------------------------------------------------------------------------ |
| **Environment**   | `environments.json` → `ground` + `vista` (+ optional `background`) | _"A soft sandy shore with a view of gentle ocean waves in the distance."_ |
| **Lighting**      | `environments.json` → `envelope` (lighting/weather portion only)   | _"Romantic golden sunset lighting."_                                      |
| **Subject**       | Subject resolution (Morphology + Identity)                         | _"A man kneeling before a woman."_                                        |
| **Clothing**      | Clothing resolution (Attire + Accessories)                         | _"Wearing a white button-down shirt and beige trousers."_                 |
| **Action**        | Relationship resolution (Actions + Pose)                           | _"Kneeling, presenting a ring box."_                                      |
| **Camera**        | Camera resolution                                                  | _"Eye-level medium shot."_                                                |
| **Style Details** | Style/Profile resolution                                           | _"Photorealistic cinematic style with vibrant red tones."_                |

---

## 4. The Assembly Order (Rendering Priority)

The final prompt must be assembled in a **strict linguistic order** to sound natural in English.

| Priority                      | Component                   | Labeled Field      | Rationale                              |
| :---------------------------- | :-------------------------- | :----------------- | :------------------------------------- |
| **1. Summary Sentence**       | Concise prose overview      | _(First line)_     | Provides immediate context.            |
| **2. Subject Core**           | Identity, Morphology        | **Subject:**       | Identify _who_ is in the scene.        |
| **3. Clothing**               | Attire, Accessories         | **Clothing:**      | Describe _what_ they are wearing.      |
| **4. Actions & Interactions** | Relationships, Pose         | **Action:**        | Describe _what_ they are doing.        |
| **5. Environment**            | Ground + Vista + Background | **Environment:**   | Describe _where_ they are.             |
| **6. Lighting**               | Envelope (Lighting/Weather) | **Lighting:**      | Describe the _atmospheric conditions_. |
| **7. Camera**                 | Framing, Angle, Depth       | **Camera:**        | Describe _how_ it is shot.             |
| **8. Style Details**          | Profile, Tone, Mood         | **Style Details:** | Describe the _aesthetic treatment_.    |

**Rule:** The **Environment** and **Lighting** fields are separated, as they originate from different keys in the atmosphere catalog (`ground`+`vista` vs `envelope`).

---

## 5. The "Vague/Scale" Edge Case (Definitive Rule)

When does an element become "too big" or "too vague" to be a Fixture?

| Element                                  | Classification                      | Reasoning                                                                              |
| :--------------------------------------- | :---------------------------------- | :------------------------------------------------------------------------------------- |
| **A Wall** (2 meters away)               | **Fixture.**                        | The Subject can touch/lean on it. It is spatially local.                               |
| **A Mountain Range** (2 kilometers away) | **Atmosphere (Vista).**             | The Subject cannot interact with it. It is a distant view.                             |
| **A Food Cart** (3 meters away)          | **Fixture.**                        | The Subject can hold it, lean on it, or buy from it.                                   |
| **"A Narrow Shopping Street"**           | **Atmosphere (Ground/Envelope).**   | It is the spatial container. The Subject is _in_ it, not interacting with it.          |
| **Pedestrians in the Background**        | **Atmosphere (Background string).** | They are filler. They do not require subject-level granularity. They are just scenery. |

**The Decisive Test:** _If you cannot write a relationship targeting it, it belongs in the Atmosphere catalog._

---

## 6. End-to-End Examples (With Eight-Field Output)

### Example 1: The Romantic Proposal (Complex)

**Scene Requirements:** Man kneeling, Woman standing, Arch framing them, Beach atmosphere.

**Input Data:**

```json
{
  "environment": "romantic_beach",
  "objects": {
    "man_1": { "type": "human", "subject": "man" },
    "woman_1": { "type": "human", "subject": "woman" },
    "rose_arch_1": {
      "type": "fixture",
      "label": "massive heart-shaped arch",
      "details": "made entirely of red roses with glowing 'Happy Valentine Day' text"
    },
    "ring_box_1": {
      "type": "item",
      "label": "small velvet ring box"
    }
  },
  "relationships": [
    { "type": "kneeling_before", "actor": "man_1", "target": "woman_1" },
    { "type": "holding", "actor": "man_1", "object": "ring_box_1" },
    {
      "type": "framing",
      "object": "rose_arch_1",
      "subjects": ["man_1", "woman_1"]
    }
  ]
}
```

**Rendered Output (Eight-Field Format):**

> _"A man kneels before a woman, holding a ring box, framed by a massive rose arch on a romantic beach at sunset."_
>
> **Subject:** _A man kneeling before a woman._
> **Clothing:** _The man wears a white button-down shirt and beige trousers; the woman wears a white floral off-shoulder dress._
> **Action:** _The man kneels, presenting a ring box, while the woman looks down with a smile._
> **Environment:** _A soft sandy shore with a view of gentle ocean waves in the distance._
> **Lighting:** _Romantic golden sunset lighting._
> **Camera:** _Eye-level medium shot capturing the couple and the rose arch._
> **Style Details:** _Photorealistic cinematic style with vibrant red tones and a dreamy romantic mood._

---

### Example 2: The Alley Wall (Handling "Vague" Fixtures)

**Scene Requirements:** Man leaning on a wall in a rainy alley.

**Input Data:**

```json
{
  "environment": "rainy_alley",
  "objects": {
    "man_1": { "type": "human", "subject": "man" },
    "wall_1": {
      "type": "fixture",
      "label": "whitewashed stone wall",
      "details": "covered in peeling paint and graffiti"
    }
  },
  "relationships": [
    { "type": "leaning_on", "actor": "man_1", "target": "wall_1" }
  ]
}
```

**`environments.json` Reference:**

```json
"rainy_alley": {
  "ground": "wet cobblestone floor",
  "envelope": "dim flickering neon light",
  "vista": "narrow alley stretching into darkness"
}
```

**Rendered Output (Eight-Field Format):**

> _"A man leans against a graffiti-covered stone wall in a rain-slicked neon alley."_
>
> **Subject:** _A man._
> **Clothing:** _[Resolved from attire]_
> **Action:** _Leaning against a whitewashed stone wall covered in peeling paint and graffiti._
> **Environment:** _A wet cobblestone floor with a view of a narrow alley stretching into darkness._
> **Lighting:** _Dim flickering neon light._
> **Camera:** _[Resolved from camera profile]_
> **Style Details:** _[Resolved from style profile]_

---

## 7. Summary of Golden Rules (The Constitution)

1.  **Separation of Concerns:** Atmosphere lives in the Flat Catalog. Fixtures live in the Scene Entities. They must never mix.
2.  **The Touch Test:** If a Subject can touch it, it must be a Fixture. If not, it must be Atmosphere.
3.  **The Background Rule:** Non-interactive background characters are just strings in the Atmosphere catalog. They are not Subjects (they lack detailed morphology/actions).
4.  **Explicit is better than implicit:** Fixtures must be explicitly defined in the scene JSON. The system does not "guess" that a table exists in a cafe.
5.  **Order matters (Eight-Field Format):** Render Actions and Fixture interactions _before_ rendering the Atmospheric Ground/Envelope/Vista. The Environment and Lighting fields are distinct and must be populated from separate keys.

---

**This document supersedes all prior environmental discussions. All future development must adhere strictly to these definitions.**
