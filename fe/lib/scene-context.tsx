'use client';

import React, { createContext, useContext, useState, useCallback } from 'react';
import { SceneState, ActorState, PropState, AtmosphereState, CameraState, EightFieldPrompt, OutlinerSelection, UIState, GroupState } from './types';

interface SceneContextType {
  scene: SceneState;
  ui: UIState;
  selection: OutlinerSelection;
  setSelection: (type: OutlinerSelection['type'], id: string | null) => void;
  setOutlinerMode: (mode: 'scene' | 'library') => void;
  updateActor: (id: string, updates: Partial<ActorState>) => void;
  addActor: (actor: ActorState) => void;
  removeActor: (id: string) => void;
  addProp: (prop: PropState) => void;
  updateProp: (id: string, updates: Partial<PropState>) => void;
  removeProp: (id: string) => void;
  updateGroup: (id: string, updates: Partial<GroupState>) => void;
  addGroup: (group: GroupState) => void;
  removeGroup: (id: string) => void;
  updateAtmosphere: (updates: Partial<AtmosphereState>) => void;
  updateCamera: (updates: Partial<CameraState>) => void;
  updateSceneName: (name: string) => void;
  loadScene: (id: string) => void;
  saveCurrentScene: () => void;
  importScene: (scene: SceneState) => void;
  savedScenesList: { id: string; name: string }[];
  deleteSceneFromStore: (id: string) => void;
  catalog: {
    subjects: Record<string, any>;
    environments: Record<string, any>;
    poses: Record<string, any>;
    attires: Record<string, any>;
    actions: Record<string, any>;
    spatial_relationships: any[];
  } | null;
  setAutoCompile: (enabled: boolean) => void;
  compileScene: (currentState?: SceneState) => void;
  resetScene: () => void;
}

const SceneContext = createContext<SceneContextType | undefined>(undefined);

const defaultScene: SceneState = {
  id: 'scene-1',
  name: 'Untitled Scene',
  actors: [],
  props: [],
  groups: [],
  atmosphere: {
    id: 'atm-1',
    preset: '',
    ground: '',
    envelope: '',
    vista: '',
    background: '',
  },
  camera: {
    id: 'cam-1',
    framing: '',
    angle: '',
    lens: '',
    depthOfField: '',
    renderProfile: '',
    mood: '',
  },
  promptOutput: 'Your prompt will appear here...',
  eightFieldPrompt: {
    subject: 'Empty scene (no actors)',
    clothing: '',
    action: '',
    environment: '',
    objects: '',
    lighting: '',
    camera: '',
    style: '',
    composition: '',
  },
  promptViewMode: 'labeled',
  autoCompile: true,
};

export function SceneProvider({ children }: { children: React.ReactNode }) {
  const [scene, setScene] = useState<SceneState>(defaultScene);
  const [ui, setUI] = useState<UIState>({
    selection: { type: null, id: null },
    outlinerMode: 'scene',
  });

  const setSelection = useCallback((type: OutlinerSelection['type'], id: string | null) => {
    setUI((prev) => ({
      ...prev,
      selection: { type, id },
    }));
  }, []);

  const setOutlinerMode = useCallback((mode: 'scene' | 'library') => {
    setUI((prev) => ({
      ...prev,
      outlinerMode: mode,
    }));
  }, []);

  const updateActor = useCallback((id: string, updates: Partial<ActorState>) => {
    setScene((prev) => ({
      ...prev,
      actors: prev.actors.map((actor) =>
        actor.id === id ? { ...actor, ...updates } : actor
      ),
    }));
  }, []);

  const addActor = useCallback((actor: ActorState) => {
    setScene((prev) => ({
      ...prev,
      actors: [...prev.actors, actor],
    }));
    setSelection('actor', actor.id);
  }, [setSelection]);

  const removeActor = useCallback((id: string) => {
    setScene((prev) => ({
      ...prev,
      actors: prev.actors.filter((actor) => actor.id !== id),
    }));
    setUI((prev) => {
      if (prev.selection.type === 'actor' && prev.selection.id === id) {
        return { ...prev, selection: { type: null, id: null } };
      }
      return prev;
    });
  }, []);

  const addProp = useCallback((prop: PropState) => {
    setScene((prev) => ({
      ...prev,
      props: [...prev.props, prop],
    }));
    setSelection('prop', prop.id);
  }, [setSelection]);

  const updateProp = useCallback((id: string, updates: Partial<PropState>) => {
    setScene((prev) => ({
      ...prev,
      props: prev.props.map((prop) =>
        prop.id === id ? { ...prop, ...updates } : prop
      ),
    }));
  }, []);

  const removeProp = useCallback((id: string) => {
    setScene((prev) => ({
      ...prev,
      props: prev.props.filter((prop) => prop.id !== id),
    }));
    setUI((prev) => {
      if (prev.selection.type === 'prop' && prev.selection.id === id) {
        return { ...prev, selection: { type: null, id: null } };
      }
      return prev;
    });
  }, []);

  const addGroup = useCallback((group: GroupState) => {
    setScene((prev) => ({
      ...prev,
      groups: [...(prev.groups || []), group],
    }));
  }, []);

  const updateGroup = useCallback((id: string, updates: Partial<GroupState>) => {
    setScene((prev) => ({
      ...prev,
      groups: (prev.groups || []).map((g) =>
        g.id === id ? { ...g, ...updates } : g
      ),
    }));
  }, []);

  const removeGroup = useCallback((id: string) => {
    setScene((prev) => ({
      ...prev,
      groups: (prev.groups || []).filter((g) => g.id !== id),
    }));
  }, []);

  const updateAtmosphere = useCallback((updates: Partial<AtmosphereState>) => {
    setScene((prev) => ({
      ...prev,
      atmosphere: { ...prev.atmosphere, ...updates },
    }));
  }, []);

  const updateCamera = useCallback((updates: Partial<CameraState>) => {
    setScene((prev) => ({
      ...prev,
      camera: { ...prev.camera, ...updates },
    }));
  }, []);

  const setPromptViewMode = useCallback((mode: 'full' | 'labeled' | 'split') => {
    setScene((prev) => ({
      ...prev,
      promptViewMode: mode,
    }));
  }, []);

  const setAutoCompile = useCallback((enabled: boolean) => {
    setScene((prev) => ({
      ...prev,
      autoCompile: enabled,
    }));
  }, []);

  const compileScene = useCallback((currentState?: SceneState) => {
    const activeScene = currentState || scene;
    
    // Construct Python-compilable JSON payload
    const camera = {
      framing: (activeScene.camera.framing || "medium").toLowerCase().replace("-", "_"),
      angle: (activeScene.camera.angle || "eye-level").toLowerCase().replace(" ", "_"),
      lens: activeScene.camera.lens || "50mm",
      depth_of_field: (activeScene.camera.depthOfField || "shallow").toLowerCase(),
    };

    const render_profile = (activeScene.camera.renderProfile || "cinematic").toLowerCase();

    const environment = activeScene.atmosphere.preset ? {
      type: activeScene.atmosphere.preset,
      ground: activeScene.atmosphere.ground || "",
      envelope: activeScene.atmosphere.envelope || "",
      vista: activeScene.atmosphere.vista || "",
      background: activeScene.atmosphere.background || "",
    } : undefined;

    const objects: Record<string, any> = {};
    const relationships: any[] = [];
    const body_config_payload: Record<string, any> = {};

    // Helper to format garment to template key
    const toTemplateKey = (garment: string, defaultKey: string) => {
      if (!garment) return defaultKey;
      let clean = garment
        .replace(/[-_]+/g, ' ')
        .replace(/(?:^\w|[A-Z]|\b\w)/g, (word) => word.toUpperCase())
        .replace(/\s+/g, '');
      if (clean.toLowerCase() === 'tshirt') return 'Tshirt';
      if (clean.toLowerCase() === 'cargopants') return 'CargoPants';
      if (clean.toLowerCase() === 'hoodie') return 'Hoodie';
      if (clean.toLowerCase() === 'sandals') return 'Sandals';
      if (clean.toLowerCase() === 'ankleboots') return 'AnkleBoots';
      if (clean.toLowerCase() === 'suitjacket' || clean.toLowerCase() === 'suit') return 'SuitJacket';
      if (clean.toLowerCase() === 'robe' || clean.toLowerCase() === 'wizardrobe') return 'WizardRobe';
      return clean || defaultKey;
    };

    activeScene.actors.forEach((actor, index) => {
      const actorId = actor.id || `actor_${index + 1}`;
      
      let subjectPreset = "urban_influencer";
      if (actor.archetype === "athlete") {
        subjectPreset = "athletic_woman";
      } else if (actor.archetype === "orc_warrior") {
        subjectPreset = "orc_warrior";
      } else if (actor.archetype === "elf_archer") {
        subjectPreset = "elf_archer";
      } else if (actor.archetype === "human") {
        if (actor.gender === "man") {
          subjectPreset = "professional_man";
        } else {
          subjectPreset = "urban_influencer";
        }
      }

      const face = actor.face?.expression ? { expression: actor.face.expression.toLowerCase() } : undefined;

      const hair = actor.hair ? {
        color: actor.hair.color?.toLowerCase(),
        length: actor.hair.length?.toLowerCase(),
        style: actor.hair.style?.toLowerCase(),
        accessory: actor.hair.accessory?.toLowerCase(),
      } : undefined;

      const morphology = actor.morphology?.skin_tone ? { skin_tone: actor.morphology.skin_tone.toLowerCase() } : undefined;

      const actorObj: any = {
        type: "human",
        subject: subjectPreset,
      };

      if (face) actorObj.Face = face;
      if (hair) actorObj.Hair = hair;
      if (actor.gender) actorObj.gender = actor.gender.toLowerCase();
      if (morphology) actorObj.morphology = morphology;

      if (actor.clothing && actor.clothing.length > 0) {
        actor.clothing.forEach((zone) => {
          if (!zone.garment) return;
          const itemId = `${actorId}_${zone.type}`;
          let zoneKey = "";
          let defaultTemplate = "UpperBody";
          if (zone.type === "upper_body") {
            zoneKey = "UpperBody";
            defaultTemplate = "UpperBody";
          } else if (zone.type === "lower_body") {
            zoneKey = "LowerBody";
            defaultTemplate = "LowerBody";
          } else if (zone.type === "feet") {
            zoneKey = "Feet";
            defaultTemplate = "Feet";
          } else if (zone.type === "hands") {
            zoneKey = "Hands";
            defaultTemplate = "Hands";
          } else if (zone.type === "headwear") {
            zoneKey = "Headwear";
            defaultTemplate = "Headwear";
          }

          if (zoneKey) {
            actorObj[zoneKey] = { owned_item_id: itemId };
            objects[itemId] = {
              type: "clothing",
              template_key: toTemplateKey(zone.garment, defaultTemplate),
              color: zone.color?.toLowerCase() || "neutral",
              material: zone.material?.toLowerCase(),
              fit: zone.fit?.toLowerCase()
            };
          }
        });
      }

      objects[actorId] = actorObj;

      const armsVal = (actor.pose?.arms || "at_side").toLowerCase().replace(" ", "_");
      const legsVal = (actor.pose?.legs || "standing").toLowerCase().replace(" ", "_");
      const gazeVal = (actor.pose?.gaze || "toward_camera").toLowerCase().replace(" ", "_");

      body_config_payload[actorId] = {
        gaze: { direction: gazeVal },
        arms: { left: armsVal, right: armsVal },
        legs: { position: legsVal }
      };

      if (actor.relationships && actor.relationships.length > 0) {
        actor.relationships.forEach((rel) => {
          if (rel.type === "holding") {
            relationships.push({
              type: "holding",
              actor: actorId,
              object: rel.targetPropId
            });
          } else if (rel.type === "leaning_on") {
            relationships.push({
              type: "leaning_on",
              actor: actorId,
              target: rel.targetPropId
            });
          } else if (rel.type === "sitting_at") {
            relationships.push({
              type: "sitting_at",
              actor: actorId,
              target: rel.targetPropId
            });
          } else if (rel.type === "standing_next_to") {
            relationships.push({
              type: "standing_next_to",
              subject: actorId,
              target: rel.targetPropId
            });
          } else if (rel.type === "kneeling_before") {
            relationships.push({
              type: "kneeling_before",
              subject1: actorId,
              subject2: rel.targetPropId
            });
          } else if (rel.type === "framing") {
            relationships.push({
              type: "framing",
              object: rel.targetPropId,
              subjects: rel.subjects || []
            });
          }
        });
      }
    });

    activeScene.props.forEach((prop) => {
      let tKey = prop.type ? prop.type.replace(/[^a-zA-Z]/g, "") : "";
      tKey = tKey.charAt(0).toUpperCase() + tKey.slice(1);
      if (!tKey) {
        tKey = prop.category === 'object' ? "Object" : "Fixture";
      }

      objects[prop.id] = {
        type: prop.category || "fixture",
        template_key: tKey,
        label: prop.label,
        details: prop.details,
        material: prop.material || undefined,
        color: prop.color || undefined,
        shape: prop.shape || undefined,
        spatial_role: prop.spatialRole || undefined,
        owner: prop.owner || undefined,
      };
    });

    const payload: any = {
      camera,
      render_profile,
      ...(environment ? { environment } : {}),
      objects,
      relationships,
      body_config: body_config_payload,
    };

    if (activeScene.groups && activeScene.groups.length > 0) {
      payload.groups = activeScene.groups.map(g => ({
        id: g.id,
        type: g.type,
        label: g.label || undefined,
        members: g.members
      }));
    }

    if (activeScene.actors.length > 0 && activeScene.actors[0].pose?.posture) {
      payload.pose = activeScene.actors[0].pose.posture.toLowerCase().replace(/ /g, "_");
    }

    // Call API
    fetch("http://localhost:8000/compile", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    })
      .then((res) => {
        if (!res.ok) throw new Error("Compilation API returned error status");
        return res.json();
      })
      .then((data) => {
        if (data.prompt && data.eightFieldPrompt) {
          setScene((prev) => ({
            ...prev,
            promptOutput: data.prompt,
            eightFieldPrompt: data.eightFieldPrompt,
          }));
        }
      })
      .catch((err) => {
        console.warn("Prompt Engine server compile failed, using local mock fallback:", err);
        // Fallback to local compile
        const eightField: EightFieldPrompt = {
          subject: '',
          clothing: '',
          action: '',
          environment: '',
          objects: '',
          lighting: '',
          camera: '',
          style: '',
          composition: '',
        };

        if (activeScene.actors.length > 0) {
          const actor = activeScene.actors[0];
          eightField.subject = `A ${actor.gender || 'person'}${
            actor.face?.expression ? ` with a ${actor.face.expression} expression` : ''
          }`;
          eightField.clothing = actor.clothing
            ?.map((zone) => `${zone.garment} in ${zone.color}`)
            .join(', ') || 'casual clothing';
          eightField.action =
            (actor.relationships?.[0]?.type as string) === 'proposal'
              ? 'proposing to someone'
              : actor.relationships?.[0]?.type || 'standing';
        } else {
          eightField.subject = 'An empty scene waiting to be composed';
        }

        eightField.environment = `On a ${activeScene.atmosphere.ground || 'surface'}${
          activeScene.atmosphere.vista ? ` with ${activeScene.atmosphere.vista.toLowerCase()}` : ''
        }`;
        eightField.lighting = activeScene.atmosphere.envelope || 'natural lighting';
        eightField.camera = `${activeScene.camera.framing} shot at ${activeScene.camera.angle}`;
        eightField.style = `${activeScene.camera.renderProfile} style`;

        const lead = `${eightField.subject}. ${eightField.clothing}. ${eightField.action}. ${eightField.environment}. ${eightField.lighting}. ${eightField.camera}. ${eightField.style}.`;
        const fullPrompt = [
          lead,
          eightField.subject ? `Subject: ${eightField.subject}` : null,
          eightField.clothing ? `Clothing: ${eightField.clothing}` : null,
          eightField.action ? `Action: ${eightField.action}` : null,
          eightField.environment ? `Environment: ${eightField.environment}` : null,
          eightField.objects ? `Objects: ${eightField.objects}` : null,
          eightField.lighting ? `Lighting: ${eightField.lighting}` : null,
          eightField.camera ? `Camera: ${eightField.camera}` : null,
          eightField.style ? `Style Details: ${eightField.style}` : null
        ].filter((x) => x !== null && x !== '').join('\n\n');

        setScene((prev) => ({
          ...prev,
          eightFieldPrompt: eightField,
          promptOutput: fullPrompt,
        }));
      });
  }, [scene]);

  React.useEffect(() => {
    if (scene.autoCompile) {
      compileScene(scene);
    }
  }, [scene.actors, scene.atmosphere, scene.camera, scene.autoCompile]);

  const [savedScenesList, setSavedScenesList] = useState<{ id: string; name: string }[]>([]);
  const [catalog, setCatalog] = useState<SceneContextType['catalog']>(null);

  // Load index of saved scenes and bootstrap data on mount
  React.useEffect(() => {
    try {
      const indexStr = localStorage.getItem('prompt_engine_scenes_index') || '[]';
      setSavedScenesList(JSON.parse(indexStr));
    } catch (e) {
      console.error("Failed to load saved scenes index", e);
    }

    fetch("http://localhost:8000/bootstrap")
      .then((res) => {
        if (!res.ok) throw new Error("Bootstrap endpoint error");
        return res.json();
      })
      .then((data) => {
        if (data.subjects && data.environments) {
          setCatalog(data);
        }
      })
      .catch((err) => {
        console.warn("Could not load backend bootstrap catalog, using local defaults:", err);
      });
  }, []);

  const updateSceneName = useCallback((name: string) => {
    setScene((prev) => ({ ...prev, name }));
  }, []);

  const saveCurrentScene = useCallback(() => {
    try {
      localStorage.setItem(`prompt_engine_scene_${scene.id}`, JSON.stringify(scene));
      const indexStr = localStorage.getItem('prompt_engine_scenes_index') || '[]';
      const index = JSON.parse(indexStr) as { id: string; name: string }[];
      if (!index.some((item) => item.id === scene.id)) {
        index.push({ id: scene.id, name: scene.name });
        localStorage.setItem('prompt_engine_scenes_index', JSON.stringify(index));
        setSavedScenesList(index);
      } else {
        const updated = index.map((item) => item.id === scene.id ? { ...item, name: scene.name } : item);
        localStorage.setItem('prompt_engine_scenes_index', JSON.stringify(updated));
        setSavedScenesList(updated);
      }
    } catch (e) {
      console.error("Failed to save current scene", e);
    }
  }, [scene]);

  const loadScene = useCallback((id: string) => {
    try {
      const sceneStr = localStorage.getItem(`prompt_engine_scene_${id}`);
      if (sceneStr) {
        const loaded = JSON.parse(sceneStr) as SceneState;
        setScene(loaded);
        setSelection(null, null);
      }
    } catch (e) {
      console.error("Failed to load scene", e);
    }
  }, [setSelection]);

  const importScene = useCallback((imported: SceneState) => {
    setScene(imported);
    setSelection(null, null);
  }, [setSelection]);

  const deleteSceneFromStore = useCallback((id: string) => {
    try {
      localStorage.removeItem(`prompt_engine_scene_${id}`);
      const indexStr = localStorage.getItem('prompt_engine_scenes_index') || '[]';
      const index = JSON.parse(indexStr) as { id: string; name: string }[];
      const filtered = index.filter((item) => item.id !== id);
      localStorage.setItem('prompt_engine_scenes_index', JSON.stringify(filtered));
      setSavedScenesList(filtered);
    } catch (e) {
      console.error("Failed to delete scene", e);
    }
  }, []);

  const resetScene = useCallback(() => {
    setScene({
      ...defaultScene,
      id: `scene-${Date.now()}`
    });
    setUI({
      selection: { type: null, id: null },
      outlinerMode: 'scene',
    });
  }, []);

  return (
    <SceneContext.Provider
      value={{
        scene,
        ui,
        selection: ui.selection,
        setSelection,
        setOutlinerMode,
        updateActor,
        addActor,
        removeActor,
        addProp,
        updateProp,
        removeProp,
        addGroup,
        updateGroup,
        removeGroup,
        updateAtmosphere,
        updateCamera,
        updateSceneName,
        loadScene,
        saveCurrentScene,
        importScene,
        savedScenesList,
        deleteSceneFromStore,
        catalog,
        setAutoCompile,
        compileScene,
        resetScene,
      }}
    >
      {children}
    </SceneContext.Provider>
  );
}

export function useScene() {
  const context = useContext(SceneContext);
  if (!context) {
    throw new Error('useScene must be used within SceneProvider');
  }
  return context;
}
