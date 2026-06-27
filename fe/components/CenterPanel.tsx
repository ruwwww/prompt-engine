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

    const actorObj: any = {
      type: "human",
      subject: subjectPreset,
    };

    if (face) actorObj.Face = face;
    if (hair) actorObj.Hair = hair;
    if (actor.gender) actorObj.gender = actor.gender.toLowerCase();

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

    if (actor.relationships && actor.relationships.length > 0) {
      actor.relationships.forEach((rel: any) => {
        const type = rel.type === "proposal" ? "proposing_to" : rel.type;
        const relationshipObj: any = {
          type: type,
          subject: actorId,
        };
        if (rel.targetPropId) {
          relationshipObj.target = rel.targetPropId;
        }
        relationships.push(relationshipObj);
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
