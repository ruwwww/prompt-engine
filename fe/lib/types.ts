export interface ClothingZone {
  id: string;
  type: 'upper_body' | 'lower_body' | 'feet' | 'hands' | 'headwear';
  garment?: string;
  color?: string;
  fit?: string;
  material?: string;
}

export interface ActorRelationship {
  id: string;
  type: 'holding' | 'sitting_at' | 'leaning_on' | 'standing_next_to' | 'framing' | 'kneeling_before';
  targetPropId?: string; // For holding, leaning, sitting, kneeling, next_to
  subjects?: string[]; // For framing: array of actor IDs
  details?: string;
}

export interface ActorState {
  id: string;
  name: string;
  archetype: string;
  gender?: string;
  morphology?: {
    skin_tone?: string;
  };
  face?: {
    expression?: string;
  };
  hair?: {
    style?: string;
    color?: string;
    length?: string;
    accessory?: string;
  };
  clothing?: ClothingZone[];
  pose?: {
    posture?: string;
    gaze?: string;
    arms?: string;
    legs?: string;
  };
  relationships?: ActorRelationship[];
}

export interface PropState {
  id: string;
  type: string;
  label: string;
  details?: string;
}

export interface AtmosphereState {
  id: string;
  preset: string;
  ground?: string;
  envelope?: string;
  vista?: string;
  background?: string;
}

export interface CameraState {
  id: string;
  framing?: string;
  angle?: string;
  lens?: string;
  depthOfField?: string;
  renderProfile?: string;
  mood?: string;
}

export interface EightFieldPrompt {
  subject: string;
  clothing: string;
  action: string;
  environment: string;
  objects?: string;
  lighting: string;
  camera: string;
  style: string;
  composition?: string;
}

export interface SceneState {
  id: string;
  name: string;
  actors: ActorState[];
  props: PropState[];
  atmosphere: AtmosphereState;
  camera: CameraState;
  promptOutput: string;
  eightFieldPrompt: EightFieldPrompt;
  promptViewMode: 'full' | 'labeled' | 'split';
  autoCompile: boolean;
}

export type SelectionType = 'actor' | 'prop' | 'atmosphere' | 'camera' | null;

export interface OutlinerSelection {
  type: SelectionType;
  id: string | null;
}

export interface UIState {
  selection: OutlinerSelection;
  outlinerMode: 'scene' | 'library';
}
