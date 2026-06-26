# Prompt Engine Studio v3 — Implementation Guide

## Overview

**Prompt Engine Studio v3** implements the **Scene Graph (Outliner) + Dynamic Inspector** architectural pattern, transforming the UI from a static library browser (v2) into an interactive scene composition tool.

---

## Architecture

### Core Pattern: Outliner + Dynamic Inspector

```
┌─────────────────────────────────────────────────────────────────┐
│                        PROMPT ENGINE STUDIO v3                   │
├──────────────┬──────────────────────────┬──────────────────────┤
│              │                          │                      │
│  OUTLINER    │     PROMPT CANVAS        │   DYNAMIC INSPECTOR  │
│              │                          │                      │
│ • Scene      │   ▸ 8-Field View         │ [Selection-driven]   │
│   Graph      │   ▸ Full Prompt          │                      │
│ • Actors     │   ▸ Split View           │ Actor Editor:        │
│ • Props      │   ▸ Live Compile         │ ├─ Archetype         │
│ • Atmosphere │                          │ ├─ Face/Hair         │
│ • Camera     │   📋 Labeled Output       │ ├─ Clothing          │
│              │                          │ ├─ Pose/Gaze         │
│ [Selection]  │                          │ └─ Relationships     │
│ ▼            │                          │                      │
└──────────────┴──────────────────────────┴──────────────────────┘
```

### State Management

All state is centralized in a single **SceneContext** with UI state:

```typescript
// Scene data
scene: {
  actors: ActorState[]
  props: PropState[]
  atmosphere: AtmosphereState
  camera: CameraState
}

// UI state (NEW in v3)
ui: {
  selection: { type: 'actor'|'prop'|'atmosphere'|'camera'|null, id: string|null }
  outlinerMode: 'scene' | 'library'
}
```

---

## Component Changes

### 1. LeftPanel — Dual-Mode Outliner + Library

**Mode Toggle (Top):**
- **📋 Scene**: Outliner view (default)
- **🗂️ Library**: Asset browser view

#### Scene Mode (Outliner)
Shows the scene hierarchy as a tree:

```
📋 SCENE: Untitled Scene
  👤 ACTORS (2)
    ▸ Man_1234 [Select to edit]
    ▸ Woman_5678 [Select to edit]
  🏺 PROPS (1)
    ▸ Rose_Arch_9012 [Select to edit]
  🌍 ATMOSPHERE: beach [Select to edit]
  📷 CAMERA: Medium Shot [Select to edit]
```

- Click any item to select it
- Selected item highlights in primary color
- Updates immediately sync to context

#### Library Mode (Asset Browser)
Tabs for browsing and adding assets:

```
Tabs: [👤] [🌍] [🏺]

[👤 Archetypes]
├─ 👩 Woman (Add button)
├─ 👨 Man (Add button)
└─ 🧑 Person (Add button)

[🌍 Atmospheres]
├─ 🏖️ Beach (Select button)
├─ 🌲 Forest (Select button)
└─ 🌃 Urban (Select button)

[🏺 Props]
├─ 💍 Ring (Add button)
├─ 🏺 Vase (Add button)
└─ 🎾 Racket (Add button)
```

- Add/Select buttons automatically:
  - Create new entity
  - Add to scene
  - Select it in Outliner
  - Switch to Scene mode

**Key Changes:**
- Removed old v2 tabs (Ensembles, Interactions, Shots, Styles)
- Unified focus on scene construction
- No selection needed before adding actors/props

---

### 2. RightPanel — Dynamic Inspector

**State-Driven Rendering:**

The right panel **re-renders completely** based on `selection`:

```typescript
if (!selection.type) → Empty placeholder
if (selection.type === 'actor') → Actor Inspector
if (selection.type === 'prop') → Prop Inspector
if (selection.type === 'atmosphere') → Atmosphere Inspector
if (selection.type === 'camera') → Camera Inspector
```

#### Actor Inspector (Selection: actor)

```
👤 [Actor Name]          [Remove Button]
─────────────────────────────────────────

ARCHETYPE
├─ [Dropdown: Woman/Man/Person]

FACE
├─ Expression: [Dropdown]

HAIR
├─ Style: [Dropdown]
├─ Color: [Dropdown]
├─ Length: [Dropdown]

CLOTHING
├─ Upper Body:
│  ├─ Garment: [Input]
│  └─ Color: [Input]
└─ Lower Body:
   ├─ Garment: [Input]
   └─ Color: [Input]

POSE & GAZE
├─ Posture: [Dropdown]
└─ Gaze: [Dropdown]

RELATIONSHIPS
├─ [List of current relationships]
└─ + Add Interaction [Button]
```

#### Prop Inspector (Selection: prop)

```
🏺 [Prop Label]                [Remove Button]
──────────────────────────────────────────────

TYPE
├─ [Input: e.g., "Arch"]

LABEL
├─ [Input: e.g., "Rose Arch"]

DETAILS
├─ [Textarea: Detailed description]
```

#### Atmosphere Inspector (Selection: atmosphere)

```
🌍 ATMOSPHERE
─────────────────

PRESET
├─ [Input: "beach"]

GROUND
├─ [Input: "Soft sandy shore"]

ENVELOPE (Lighting)
├─ [Input: "Golden sunset"]

VISTA (Background)
├─ [Input: "Ocean waves"]

BACKGROUND
├─ [Input: "Seabirds gliding (optional)"]
```

#### Camera Inspector (Selection: camera)

```
📷 CAMERA & STYLE
──────────────────

FRAMING
├─ [Dropdown: Close-up/Medium/Full-body/Wide]

ANGLE
├─ [Dropdown: Eye-level/Low-angle/High-angle/Dutch]

RENDER PROFILE
├─ [Dropdown: Cinematic/Natural/Stylized]

MOOD
├─ [Dropdown: Neutral/Dramatic/Romantic/Dark/Bright]
```

**Key Changes:**
- No collapsible sections (cleaner layout)
- Direct form inputs for all properties
- Dropdowns for standard options
- Textareas for detailed descriptions
- All fields update live to context

---

### 3. CenterPanel — Unchanged (Works as-is)

The Prompt Canvas remains the same:
- 8-Field View (default)
- Full Prompt View
- Split View
- Live compilation

---

## Context API (New UIState)

### Types Added

```typescript
// lib/types.ts
export type SelectionType = 'actor' | 'prop' | 'atmosphere' | 'camera' | null;

export interface OutlinerSelection {
  type: SelectionType;
  id: string | null;
}

export interface UIState {
  selection: OutlinerSelection;
  outlinerMode: 'scene' | 'library';
}
```

### New Context Methods

```typescript
// Select an entity
setSelection(type: SelectionType, id: string | null) => void

// Toggle Outliner mode
setOutlinerMode(mode: 'scene' | 'library') => void
```

### State Updates on Actions

**When adding an actor:**
```typescript
addActor(newActor) {
  setScene(prev => ({ ...prev, actors: [...prev.actors, newActor] }))
  setSelection('actor', newActor.id)  // Auto-select in inspector
  setOutlinerMode('scene')            // Switch to Outliner view
}
```

**When removing a selected entity:**
```typescript
removeActor(id) {
  // Remove from scene
  // Clear selection if it was selected
  setUI(prev => {
    if (prev.selection.type === 'actor' && prev.selection.id === id) {
      return { ...prev, selection: { type: null, id: null } }
    }
    return prev;
  })
}
```

---

## User Flows

### Workflow 1: Create Scene with Multiple Actors

1. Start in **Outliner** (default)
2. See empty scene graph
3. Click 🗂️ Library button → Switch to asset browser
4. Click 👤 tab → Shows archetypes
5. Click "Add" on Woman → Creates woman actor, selects it, switches to Scene
6. Right panel shows **Actor Inspector** for Woman_1234
7. Configure: archetype, face, hair, clothing, pose
8. Click 🗂️ Library again → Add Man
9. Now Outliner shows both actors:
   - 👤 Woman_1234 (current selection)
   - 👤 Man_5678 (not selected)
10. Click on Man_5678 in Outliner → Inspector updates to show Man's properties
11. Configure Man's properties
12. Click 🌍 Atmosphere → Inspector switches to atmosphere editor

### Workflow 2: Edit Existing Scene

1. Outliner shows scene graph with existing actors/props
2. Click on an actor name → Inspector updates
3. Edit clothing/face/pose in dropdowns
4. Changes auto-compile to Prompt Canvas
5. Switch to 📋 Scene details panel to see changes reflected
6. Click Camera in Outliner → Switch to camera/style inspector
7. Adjust framing and mood

### Workflow 3: Add Prop to Scene

1. Outliner mode
2. Click 🗂️ Library
3. Click 🏺 Props tab
4. Click "Add" on Ring → Prop added to scene, selected
5. Right panel shows **Prop Inspector**
6. Enter label: "Heart-shaped diamond ring"
7. Enter details: "Glowing with soft white light"
8. Back to Outliner, see 🏺 PROPS (1) with new ring listed

---

## Technical Details

### Selection Propagation

Selection is stored in `UIState` and accessed via context:

```typescript
const { ui, selection, setSelection } = useScene();

// Reading selection
if (selection.type === 'actor') {
  const actor = scene.actors.find(a => a.id === selection.id);
  // Show actor inspector
}

// Setting selection
onClick={() => setSelection('actor', actor.id)}
```

### Dynamic Inspector Pattern

RightPanel uses a series of if-statements to render different inspectors:

```typescript
export function RightPanel() {
  const { selection } = useScene();

  if (!selection.type) {
    return <EmptyPlaceholder />;
  }

  if (selection.type === 'actor') {
    return <ActorInspector />;
  }

  if (selection.type === 'prop') {
    return <PropInspector />;
  }

  // ... etc
}
```

This ensures:
- **Only one inspector rendered at a time** (clean, focused UI)
- **Zero state management in RightPanel** (stateless, data-driven)
- **Context updates → Inspector re-renders automatically** (reactive)

### Library Mode Logic

Adding from Library:

```typescript
const handleAddArchetype = (archetypeId: string) => {
  const archetype = mockArchetypes.find(a => a.id === archetypeId);
  const newActor: ActorState = { /* ... */ };
  
  addActor(newActor);           // Updates scene AND selection
  setOutlinerMode('scene');     // Auto-switch to Outliner
}
```

This creates a smooth workflow: browse → add → auto-select → edit in inspector.

---

## Key Improvements Over v2

| Feature | v2 | v3 |
|---------|----|----|
| **Primary Panel** | Library browser (7 tabs) | Scene graph (Outliner) |
| **Selection** | Manual, no visual feedback | Auto-select, highlighted |
| **Inspector** | Static collapsibles | Dynamic, selection-driven |
| **Add Workflow** | Browse → Click → Manually select | Browse → Click → Auto-select |
| **Scene Visibility** | Hidden in tabs | Always visible in Outliner |
| **Inspector Focus** | Multiple entities at once | One entity at a time |
| **UI Clarity** | Cluttered tabs | Focused, binary mode toggle |

---

## Testing the v3 Pattern

### Quick Test Checklist

- [ ] Start app → Outliner visible
- [ ] Click "🗂️ Library" → Library appears
- [ ] Click "📋 Scene" → Back to Outliner
- [ ] Library → Click "Add" on an archetype → Actor added, auto-selected, Outliner shown
- [ ] Click actor in Outliner → Actor Inspector appears
- [ ] Modify clothing → Changes appear in right panel
- [ ] Switch to Library → Library persists
- [ ] Click Atmosphere in Outliner → Atmosphere Inspector shown
- [ ] Click Camera in Outliner → Camera Inspector shown
- [ ] No selection → Empty placeholder shown

---

## Files Modified

- `lib/types.ts` — Added `SelectionType`, `OutlinerSelection`, `UIState`
- `lib/scene-context.tsx` — Added UI state management, `setSelection`, `setOutlinerMode`
- `components/LeftPanel.tsx` — Complete rewrite: Outliner + Library dual-mode
- `components/RightPanel.tsx` — Complete rewrite: Dynamic, selection-driven inspector

---

## Design Philosophy

**v3 follows three core principles:**

1. **Single Source of Truth (Outliner)**
   - The scene graph is the primary view
   - All entities listed hierarchically
   - Clear visual feedback on selection

2. **Dynamic Inspector Pattern**
   - Inspector content changes based on selection
   - One entity at a time (focused editing)
   - No context switching

3. **Smooth Workflows**
   - Library mode for browsing assets
   - Auto-select after adding
   - Instant visual feedback
   - Live compilation

---

## Future Enhancements

- Drag-and-drop reordering in Outliner
- Relationship visualization (arrows showing connections)
- Batch operations (select multiple actors)
- Search/filter in Outliner
- Undo/redo stack
- Scene history timeline
- Export/import scene graphs

---

*Prompt Engine Studio v3 — Built with React 19, Tailwind CSS, and the Scene Graph + Dynamic Inspector pattern.*
