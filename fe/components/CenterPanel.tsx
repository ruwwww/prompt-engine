'use client';

import React, { useState, useEffect } from 'react';
import { useScene } from '@/lib/scene-context';
import { Button } from '@/components/ui/button';
import { Toggle } from '@/components/ui/toggle';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Copy, Volume2 } from 'lucide-react';

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

function buildScenePayload(activeScene: any) {
  const camera = {
    framing: (activeScene.camera.framing || "medium").toLowerCase().replace("-", "_"),
    angle: (activeScene.camera.angle || "eye-level").toLowerCase().replace(" ", "_"),
    lens: activeScene.camera.lens || "50mm",
    depth_of_field: (activeScene.camera.depthOfField || "shallow").toLowerCase(),
  };

  const render_profile = (activeScene.camera.renderProfile || "cinematic").toLowerCase();

  const environment = {
    type: activeScene.atmosphere.preset || "beach",
    ground: activeScene.atmosphere.ground || "",
    envelope: activeScene.atmosphere.envelope || "",
    vista: activeScene.atmosphere.vista || "",
    background: activeScene.atmosphere.background || "",
  };

  const objects: Record<string, any> = {};
  const relationships: any[] = [];
  const body_config_payload: Record<string, any> = {};

  activeScene.actors.forEach((actor: any, index: number) => {
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
      actor.clothing.forEach((zone: any) => {
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
      actor.relationships.forEach((rel: any) => {
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

  activeScene.props.forEach((prop: any) => {
    let tKey = prop.type.replace(/[^a-zA-Z]/g, "");
    tKey = tKey.charAt(0).toUpperCase() + tKey.slice(1);
    if (!tKey) tKey = "Fixture";

    objects[prop.id] = {
      type: "fixture",
      template_key: tKey,
      label: prop.label,
      details: prop.details,
    };
  });

  const payload: any = {
    camera,
    render_profile,
    environment,
    objects,
    relationships,
    body_config: body_config_payload,
  };

  if (activeScene.actors.length > 0 && activeScene.actors[0].pose?.posture) {
    payload.pose = activeScene.actors[0].pose.posture.toLowerCase().replace(/ /g, "_");
  }

  return payload;
}

export function CenterPanel() {
  const { scene, setAutoCompile, compileScene } = useScene();
  const [copied, setCopied] = useState(false);
  const [copiedInput, setCopiedInput] = useState(false);
  const [copiedResolved, setCopiedResolved] = useState(false);
  const [viewMode, setViewMode] = useState<'breakdown' | 'json'>('breakdown');
  const [resolvedJson, setResolvedJson] = useState<string>('{}');
  const [validationResult, setValidationResult] = useState<{
    show: boolean;
    valid: boolean;
    errors: { field: string; msg: string; value: any }[];
    message: string;
  } | null>(null);

  const handleValidate = () => {
    fetch("http://localhost:8000/validate", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    })
      .then((res) => {
        if (!res.ok) throw new Error("Validation API error");
        return res.json();
      })
      .then((data) => {
        setValidationResult({
          show: true,
          valid: data.valid,
          errors: data.errors || [],
          message: data.message,
        });
      })
      .catch((err) => {
        setValidationResult({
          show: true,
          valid: false,
          errors: [],
          message: "⚠️ Validation service unavailable. Is the backend running?",
        });
      });
  };

  const payload = buildScenePayload(scene);

  useEffect(() => {
    if (viewMode === 'json') {
      fetch("http://localhost:8000/resolve", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      })
        .then((res) => {
          if (!res.ok) throw new Error("Resolve API error");
          return res.json();
        })
        .then((data) => {
          if (data.resolved) {
            setResolvedJson(JSON.stringify(data.resolved, null, 2));
          }
        })
        .catch((err) => {
          console.error("Failed to resolve scene for debug view:", err);
        });
    }
  }, [scene, viewMode]);

  const handleCopy = () => {
    navigator.clipboard.writeText(scene.promptOutput);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleCopyInput = () => {
    navigator.clipboard.writeText(JSON.stringify(payload, null, 2));
    setCopiedInput(true);
    setTimeout(() => setCopiedInput(false), 2000);
  };

  const handleCopyResolved = () => {
    navigator.clipboard.writeText(resolvedJson);
    setCopiedResolved(true);
    setTimeout(() => setCopiedResolved(false), 2000);
  };

  const wordCount = scene.promptOutput.split(/\s+/).filter(w => w.length > 0).length;

  return (
    <div className="flex-1 border-r border-border bg-background flex flex-col h-full">
      {/* Header */}
      <div className="p-2 border-b border-border flex items-center justify-between gap-2 h-11">
        <div className="flex items-center gap-1">
          <Button
            size="sm"
            variant={viewMode === 'breakdown' ? 'default' : 'ghost'}
            className="text-xs h-7 px-2 font-semibold"
            onClick={() => setViewMode('breakdown')}
          >
            📋 8-Field Breakdown
          </Button>
          <Button
            size="sm"
            variant={viewMode === 'json' ? 'default' : 'ghost'}
            className="text-xs h-7 px-2 font-semibold"
            onClick={() => setViewMode('json')}
          >
            🔍 JSON Debug
          </Button>
        </div>

        <Toggle
          pressed={scene.autoCompile}
          onPressedChange={setAutoCompile}
          size="sm"
          className="h-8 px-2"
          aria-label="Auto compile"
          title="Auto-compile mode"
        >
          ⚡
        </Toggle>
      </div>

      {/* Validation Result Alert Banner */}
      {validationResult?.show && (
        <div className={`p-2.5 border-b text-xs flex flex-col gap-1 transition-all ${
          validationResult.valid 
            ? 'bg-green-500/10 border-green-500/20 text-green-400' 
            : 'bg-red-500/10 border-red-500/20 text-red-400'
        }`}>
          <div className="flex items-center justify-between font-semibold">
            <span>{validationResult.message}</span>
            <button 
              onClick={() => setValidationResult(null)} 
              className="text-[10px] opacity-70 hover:opacity-100 px-1 py-0.5 rounded bg-muted/20 hover:bg-muted/40"
            >
              Close
            </button>
          </div>
          {validationResult.errors.length > 0 && (
            <ul className="list-disc list-inside space-y-0.5 mt-1 font-mono text-[10px] max-h-32 overflow-y-auto bg-black/10 p-1.5 rounded">
              {validationResult.errors.map((err, i) => (
                <li key={i}>
                  <span className="font-bold text-foreground">{err.field}</span>: {err.msg} {err.value !== undefined && err.value !== null && <span className="opacity-60">(got: {JSON.stringify(err.value)})</span>}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {/* Content: 8-Field breakdown or Side-by-side JSON Debug viewer */}
      {viewMode === 'breakdown' ? (
        <div className="flex-1 overflow-hidden">
          <ScrollArea className="w-full h-full">
            <div className="p-4 space-y-3">
              {[
                { label: 'Subject', value: scene.eightFieldPrompt.subject === 'Empty scene (no actors)' ? '' : scene.eightFieldPrompt.subject, placeholder: 'No subject / actors added' },
                { label: 'Clothing', value: scene.eightFieldPrompt.clothing, placeholder: 'No clothing specified' },
                { label: 'Action', value: scene.eightFieldPrompt.action, placeholder: 'No action specified' },
                { label: 'Objects', value: scene.eightFieldPrompt.objects, placeholder: 'No objects in the scene' },
                { label: 'Environment', value: scene.eightFieldPrompt.environment, placeholder: 'No environment preset selected' },
                { label: 'Lighting', value: scene.eightFieldPrompt.lighting, placeholder: 'No lighting specified' },
                { label: 'Camera', value: scene.eightFieldPrompt.camera, placeholder: 'No camera shot selected' },
                { label: 'Style', value: scene.eightFieldPrompt.style, placeholder: 'No render style selected' },
                { label: 'Composition', value: scene.eightFieldPrompt.composition, placeholder: 'Balanced (default)' },
              ].map((field) => {
                const hasValue = !!field.value;
                return (
                  <div key={field.label} className="space-y-1">
                    <label className="text-xs font-semibold text-muted-foreground">
                      {field.label}
                    </label>
                    <p className={`text-sm p-2 bg-muted/20 rounded border border-border transition-colors ${
                      hasValue ? 'text-foreground font-medium' : 'text-muted-foreground/50 italic select-none'
                    }`}>
                      {field.value || field.placeholder}
                    </p>
                  </div>
                );
              })}
            </div>
          </ScrollArea>
        </div>
      ) : (
        <div className="flex-1 flex gap-2 p-3 min-h-0 overflow-hidden">
          <div className="flex-1 flex flex-col min-w-0 h-full">
            <div className="flex justify-between items-center mb-1">
              <span className="text-[10px] uppercase tracking-wider text-muted-foreground font-bold">
                Scene JSON (user input)
              </span>
              <Button
                size="xs"
                variant="ghost"
                className="h-5 px-1.5 text-[9px] font-mono text-muted-foreground hover:text-foreground"
                onClick={handleCopyInput}
              >
                {copiedInput ? 'Copied!' : 'Copy'}
              </Button>
            </div>
            <ScrollArea className="flex-grow border border-border rounded bg-muted/10 p-2 h-full">
              <pre className="text-xs text-blue-400 font-mono whitespace-pre-wrap">
                {JSON.stringify(payload, null, 2)}
              </pre>
            </ScrollArea>
          </div>
          <div className="flex-1 flex flex-col min-w-0 h-full">
            <div className="flex justify-between items-center mb-1">
              <span className="text-[10px] uppercase tracking-wider text-teal-400 font-bold">
                Resolved (deep merge)
              </span>
              <Button
                size="xs"
                variant="ghost"
                className="h-5 px-1.5 text-[9px] font-mono text-muted-foreground hover:text-foreground"
                onClick={handleCopyResolved}
              >
                {copiedResolved ? 'Copied!' : 'Copy'}
              </Button>
            </div>
            <ScrollArea className="flex-grow border border-border rounded bg-teal-950/10 p-2 h-full">
              <pre className="text-xs text-teal-400 font-mono whitespace-pre-wrap">
                {resolvedJson}
              </pre>
            </ScrollArea>
          </div>
        </div>
      )}

      {/* Footer */}
      <div className="p-2 border-t border-border flex items-center justify-between gap-2">
        <div className="text-xs text-muted-foreground">
          {wordCount} words • {scene.actors.length} actors
        </div>
        <div className="flex gap-1">
          <Button
            size="sm"
            variant="outline"
            className="text-xs h-7 gap-1"
            onClick={handleValidate}
          >
            🔍 Validate JSON
          </Button>
          <Button
            size="sm"
            variant="outline"
            className="text-xs h-7 gap-1"
            onClick={() => compileScene()}
          >
            ⚡ Compile
          </Button>
          <Button
            size="sm"
            variant="outline"
            className="text-xs h-7 gap-1"
            onClick={handleCopy}
          >
            <Copy className="w-3 h-3" />
            {copied ? 'Copied' : 'Copy'}
          </Button>
          <Button
            size="sm"
            variant="outline"
            className="text-xs h-7 gap-1"
            title="Read aloud"
          >
            <Volume2 className="w-3 h-3" />
          </Button>
        </div>
      </div>
    </div>
  );
}
