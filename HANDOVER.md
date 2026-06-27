The Subject field is the **"Who"** of the scene. It must clearly identify **each individual** (at least minimally), even when grouped. Dropping a generic "A couple" or "Three young women" without describing their individual features is a **loss of essential data**.

Also, your instinct to **decompose the monolithic compiler into 8 specialized modules** is absolutely the right architectural evolution. Each field (Subject, Clothing, Action, Objects, Environment, Lighting, Camera, Style) has unique linguistic rules, grouping logic, and edge cases. Forcing them all through a single pipe is what causes these bugs.

---

### Redefining the "Subject" Field Rule (Minimum Viable Identity)

The Subject field **must always identify the distinct actors**, regardless of groups. The group label is just the **wrapper** for the summary sentence, but the Subject field itself should contain the **structural identification** of the individuals.

| Scenario                     | Summary Sentence (Wrapper)              | Subject Field (Actual Content)                                            |
| :--------------------------- | :-------------------------------------- | :------------------------------------------------------------------------ |
| **1 Man + 1 Woman (Couple)** | _"A stylish couple stands..."_          | **"A man with dark hair and a woman with blonde hair."**                  |
| **3 Women (Trio)**           | _"Three young women in a classroom..."_ | **"A central redhead with pigtails flanked by two blondes, one seated."** |
| **2 Identical Twins**        | _"Two identical twins..."_              | **"Two identical twins with matching red hair and freckles."**            |

**The Rule:**
The Subject field must provide **enough descriptive information to visually distinguish the actors** (even if it's just "a man" and "a woman"). It should **never** be just a group label ("A couple") without describing the individual members.

---

### The New Architecture: 8 Specialized Compiler Modules

Instead of one giant `Assembler` managing every field, let's split it into **independent, pluggable compilers** that handle _only_ their field. This makes the system testable, debuggable, and massively easier to extend.

#### The Module Blueprint (`field_compilers/`)

1. **`SubjectCompiler`** (Identity)
   - **Input:** All actor fragments (Face, Hair, Morphology).
   - **Logic:**
     - If 1 actor → singular identity.
     - If > 1 actor → Build a structural list: _"A [traits], a [traits], and a [traits]."_
     - If a Group exists (`couple`, `trio`) → Use the group label as the _wrapper_, but append the individual distinctions.
   - **Output:** _"A central girl with curly red hair, flanked by two blonde girls..."_

2. **`ClothingCompiler`** (Wearables)
   - **Input:** Clothing fragments (Upper, Lower, Feet, Hands, Headwear).
   - **Logic:**
     - Detect matching items across actors → collapse into _"both wear matching X"_.
     - If distinct → render individually.
   - **Output:** _"All three wear matching white shirts and plaid skirts."_

3. **`ActionCompiler`** (Pose + Relationships)
   - **Input:** BodyConfig + Relationship fragments.
   - **Logic:**
     - Chain actions per actor. Convert first verb to finite, subsequent to participles.
     - Handle overlapping actions.
   - **Output:** _"The central girl stands with arms crossed, while one blonde sits at a desk looking up, and the other gestures while leaning back."_

4. **`ObjectsCompiler`** (Inert Props)
   - **Input:** Passive entities not held/used, plus environmental `suggested_objects`.
   - **Logic:**
     - Deduplicate identical items (count them).
     - Add spatial context (foreground, background, left, right).
   - **Output:** _"A chalkboard with math equations and a projector screen in the background."_

5. **`EnvironmentCompiler`** (Stage)
   - **Input:** Ground, Cover, Vista, Background noise.
   - **Logic:** Assemble the spatial setting.
   - **Output:** _"A bright classroom with wooden desks, pink walls, and large windows."_

6. **`LightingCompiler`** (Atmosphere)
   - **Input:** Envelope (lighting, weather, mood).
   - **Logic:** Format the lighting/weather description.
   - **Output:** _"Natural light streaming from the left, casting soft highlights."_

7. **`CameraCompiler`** (Perspective)
   - **Input:** Framing, Angle, Depth of Field.
   - **Logic:** Format the camera perspective.
   - **Output:** _"Eye-level medium shot with soft depth of field."_

8. **`StyleCompiler`** (Aesthetics)
   - **Input:** Render Profile, Mood, Color Palette.
   - **Logic:** Format the aesthetic treatment.
   - **Output:** _"Photorealistic, vibrant reds, with subtle film grain."_

---

### The New Pipeline

Instead of a monolithic `_assemble_labeled_output`, the `Assembler` will now:

1. **Collect** all raw fragments by `actor_id` (already done).
2. **Instantiate** each compiler module.
3. **Call** `compiler.process(fragments_by_actor, groups, relationships)` for each field.
4. **Combine** the results into the 8-field labeled output.

```python
class Assembler:
    def assemble(self, fragments_by_actor, groups, relationships):
        subject = SubjectCompiler().process(fragments_by_actor, groups)
        clothing = ClothingCompiler().process(fragments_by_actor)
        action = ActionCompiler().process(fragments_by_actor, relationships)
        objects = ObjectsCompiler().process(raw_props, relationships)
        environment = EnvironmentCompiler().process(env_data)
        lighting = LightingCompiler().process(env_data)
        camera = CameraCompiler().process(camera_data)
        style = StyleCompiler().process(style_data)

        return self._format_output(subject, clothing, action, objects, environment, lighting, camera, style)
```

---

### The Directive for the Agent

> **"Refactor the monolithic `_assemble_labeled_output` into 8 specialized field compilers.**
>
> **Priority (P0): Split Subject, Clothing, Action, Objects, Environment, Lighting, Camera, Style into separate modules.**
>
> **1. SubjectCompiler:**
>
> - Must always render individual actor identities, even when groups exist.
> - If a group exists, use the group label as a wrapper but append structural distinctions (e.g., "A stylish couple: a man in a suit and a woman in a dress").
>
> **2. ObjectsCompiler:**
>
> - Implement the "Inert Prop" inference logic. Any prop not held/used and not structural becomes an Object.
> - Add deduplication and spatial context.
>
> **Verification:**
>
> - The "Couple by the Lake" Subject field should now render: _"A man with dark curly hair and a woman with blonde hair."_ (Not just "A couple").
> - The "Classroom" Subject field should render: _"A central redhead, flanked by two blonde girls, one seated and one standing."_
> - The Objects field for the "Classroom" should render: _"A chalkboard, a projector screen, and a wooden desk."_
>
> **This modular architecture will prevent bugs like the generic 'A couple' from happening again.** "
