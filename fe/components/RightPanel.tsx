'use client';

import React, { useState } from 'react';
import { useScene } from '@/lib/scene-context';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  SelectGroup,
  SelectLabel,
} from '@/components/ui/select';
import { mockArchetypes, mockGarments, mockAtmospheres } from '@/lib/mock-data';
import { ClothingClosetModal } from '@/components/ClothingClosetModal';

export function RightPanel() {
  const { scene, ui, selection, updateActor, updateProp, updateAtmosphere, updateCamera, removeActor, removeProp, catalog } =
    useScene();

  const [closetOpen, setClosetOpen] = useState(false);
  const [closetZone, setClosetZone] = useState<'upper_body' | 'lower_body' | 'feet' | 'hands' | 'headwear'>('upper_body');

  // Dynamically resolve archetypes from backend subjects data
  const archetypes = catalog?.subjects
    ? Object.keys(catalog.subjects).map((key) => ({
        id: key,
        name: key.replace(/_/g, ' ').replace(/\b\w/g, (c: string) => c.toUpperCase()),
        icon: key.includes('orc') ? '👹' : key.includes('elf') ? '🧝' : key.includes('influencer') || key.includes('woman') || key.includes('creative') ? '👩' : '👨',
      }))
    : mockArchetypes;

  // Dynamically resolve atmospheres from backend environments data
  const atmospheres = catalog?.environments
    ? Object.keys(catalog.environments).map((key) => {
        const env = catalog.environments[key];
        return {
          id: key,
          name: env.label ? env.label.replace(/\b\w/g, (c: string) => c.toUpperCase()) : key.replace(/_/g, ' ').replace(/\b\w/g, (c: string) => c.toUpperCase()),
          icon: key.includes('beach') ? '🏖️' : key.includes('cafe') ? '☕' : key.includes('alley') ? '🌆' : key.includes('forest') ? '🌳' : '🌍',
          preset: key,
          ground: env.primary_surface?.material || 'surface',
          envelope: env.default_lighting || 'natural light',
          vista: env.default_weather || '',
          background: '',
        };
      })
    : mockAtmospheres;

  // Collapsible state for actor inspector sections
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    archetype: true,
    face: true,
    hair: true,
    clothing: true,
    pose: true,
    relationships: true,
  });

  const toggleSection = (section: string) => {
    setExpandedSections((prev) => ({
      ...prev,
      [section]: !prev[section],
    }));
  };

  // No selection - show placeholder
  if (!selection.type || !selection.id) {
    return (
      <div className="w-80 border-l border-border bg-background flex flex-col h-full">
        <div className="p-4 flex items-center justify-center h-full text-center">
          <div className="space-y-2 select-none">
            <div className="text-sm text-muted-foreground">Select an entity from the Outliner</div>
            <div className="text-xs text-muted-foreground">to view and edit properties</div>
          </div>
        </div>
      </div>
    );
  }

  // Actor Inspector
  if (selection.type === 'actor') {
    const actor = scene.actors.find((a) => a.id === selection.id);
    if (!actor) return null;

    return (
      <>
        <div className="w-80 border-l border-border bg-background flex flex-col h-full">
          {/* Header */}
          <div className="p-3 border-b border-border flex items-center justify-between">
            <h3 className="text-sm font-semibold truncate max-w-[180px]">👤 {actor.name}</h3>
            <Button
              size="sm"
              variant="destructive"
              className="h-6 text-xs animate-in fade-in"
              onClick={() => removeActor(actor.id)}
            >
              Remove
            </Button>
          </div>

          {/* Form Content (scrollable div) */}
          <div className="flex-1 overflow-y-auto p-3 space-y-3">
            
            {/* 1. ARCHETYPE PANEL */}
            <div className="border border-border rounded-lg overflow-hidden bg-card">
              <button
                onClick={() => toggleSection('archetype')}
                className="w-full p-2 bg-muted/30 hover:bg-muted/50 flex items-center justify-between text-xs font-bold text-foreground select-none transition-colors"
              >
                <span>👤 ARCHETYPE</span>
                <span className="text-[10px]">{expandedSections.archetype ? '▼' : '▶'}</span>
              </button>
              {expandedSections.archetype && (
                <div className="p-3 border-t border-border space-y-2">
                  <Select
                    value={actor.archetype}
                    onValueChange={(value) => updateActor(actor.id, { archetype: value || undefined })}
                  >
                    <SelectTrigger className="h-8 text-xs w-full">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {archetypes.map((arch) => (
                        <SelectItem key={arch.id} value={arch.id}>
                          {arch.icon} {arch.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>

                  <div className="grid grid-cols-2 gap-2 mt-2 pt-2 border-t border-border/50">
                    {/* Gender Selector */}
                    <div className="space-y-1">
                      <label className="text-[10px] text-muted-foreground font-bold uppercase">Gender</label>
                      <Select
                        value={actor.gender || 'woman'}
                        onValueChange={(value) => updateActor(actor.id, { gender: value })}
                      >
                        <SelectTrigger className="h-7 text-xs w-full">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="man">Man</SelectItem>
                          <SelectItem value="woman">Woman</SelectItem>
                          <SelectItem value="non-binary">Non-binary</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>

                    {/* Skin Tone Selector */}
                    <div className="space-y-1">
                      <label className="text-[10px] text-muted-foreground font-bold uppercase">Skin Tone</label>
                      <Select
                        value={actor.morphology?.skin_tone || 'olive'}
                        onValueChange={(value) =>
                          updateActor(actor.id, {
                            morphology: { ...actor.morphology, skin_tone: value }
                          })
                        }
                      >
                        <SelectTrigger className="h-7 text-xs w-full">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="fair">Fair</SelectItem>
                          <SelectItem value="olive">Olive</SelectItem>
                          <SelectItem value="dark">Dark</SelectItem>
                          <SelectItem value="alabaster">Alabaster</SelectItem>
                          <SelectItem value="warm">Warm</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* 2. FACE PANEL */}
            <div className="border border-border rounded-lg overflow-hidden bg-card">
              <button
                onClick={() => toggleSection('face')}
                className="w-full p-2 bg-muted/30 hover:bg-muted/50 flex items-center justify-between text-xs font-bold text-foreground select-none transition-colors"
              >
                <span>😊 FACE</span>
                <span className="text-[10px]">{expandedSections.face ? '▼' : '▶'}</span>
              </button>
              {expandedSections.face && (
                <div className="p-3 border-t border-border space-y-2">
                  <Select
                    value={actor.face?.expression || 'Neutral'}
                    onValueChange={(value) =>
                      updateActor(actor.id, {
                        face: { ...actor.face, expression: value || undefined },
                      })
                    }
                  >
                    <SelectTrigger className="h-8 text-xs w-full">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="Neutral">😐 Neutral</SelectItem>
                      <SelectItem value="Smiling">😊 Smiling</SelectItem>
                      <SelectItem value="Snarling">😡 Snarling</SelectItem>
                      <SelectItem value="Surprised">😮 Surprised</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              )}
            </div>

            {/* 3. HAIR PANEL */}
            <div className="border border-border rounded-lg overflow-hidden bg-card">
              <button
                onClick={() => toggleSection('hair')}
                className="w-full p-2 bg-muted/30 hover:bg-muted/50 flex items-center justify-between text-xs font-bold text-foreground select-none transition-colors"
              >
                <span>💇 HAIR</span>
                <span className="text-[10px]">{expandedSections.hair ? '▼' : '▶'}</span>
              </button>
              {expandedSections.hair && (
                <div className="p-3 border-t border-border space-y-2">
                  <div className="space-y-2">
                    <Select
                      value={actor.hair?.style || 'Straight'}
                      onValueChange={(value) =>
                        updateActor(actor.id, {
                          hair: { ...actor.hair, style: value || undefined },
                        })
                      }
                    >
                      <SelectTrigger className="h-7 text-xs w-full">
                        <SelectValue placeholder="Style" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="Straight">Straight</SelectItem>
                        <SelectItem value="Wavy">Wavy</SelectItem>
                        <SelectItem value="Curly">Curly</SelectItem>
                        <SelectItem value="Braids">Braids</SelectItem>
                        <SelectItem value="Ponytail">Ponytail</SelectItem>
                      </SelectContent>
                    </Select>

                    <Select
                      value={actor.hair?.color || 'Brown'}
                      onValueChange={(value) =>
                        updateActor(actor.id, {
                          hair: { ...actor.hair, color: value || undefined },
                        })
                      }
                    >
                      <SelectTrigger className="h-7 text-xs w-full">
                        <SelectValue placeholder="Color" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="Black">Black</SelectItem>
                        <SelectItem value="Brown">Brown</SelectItem>
                        <SelectItem value="Blonde">Blonde</SelectItem>
                        <SelectItem value="Red">Red</SelectItem>
                        <SelectItem value="Silver">Silver</SelectItem>
                      </SelectContent>
                    </Select>

                    <Select
                      value={actor.hair?.length || 'Medium'}
                      onValueChange={(value) =>
                        updateActor(actor.id, {
                          hair: { ...actor.hair, length: value || undefined },
                        })
                      }
                    >
                      <SelectTrigger className="h-7 text-xs w-full">
                        <SelectValue placeholder="Length" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="Short">Short</SelectItem>
                        <SelectItem value="Medium">Medium</SelectItem>
                        <SelectItem value="Long">Long</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              )}
            </div>

            {/* 4. CLOTHING PANEL */}
            <div className="border border-border rounded-lg overflow-hidden bg-card">
              <button
                onClick={() => toggleSection('clothing')}
                className="w-full p-2 bg-muted/30 hover:bg-muted/50 flex items-center justify-between text-xs font-bold text-foreground select-none transition-colors"
              >
                <span>👕 CLOTHING</span>
                <span className="text-[10px]">{expandedSections.clothing ? '▼' : '▶'}</span>
              </button>
              {expandedSections.clothing && (
                <div className="p-3 border-t border-border space-y-2">
                  <div className="space-y-2.5">
                    {actor.clothing?.map((zone) => {
                      const zoneType = zone.type as keyof typeof mockGarments;
                      const availableGarments = mockGarments[zoneType] || [];
                      const currentGarment = availableGarments.find(g => g.name === zone.garment);
                      const availableColors = currentGarment?.colors || [];

                      return (
                        <div key={zone.id} className="text-xs space-y-1.5 p-2 bg-muted/20 rounded border border-border/50">
                          <div className="flex items-center justify-between">
                            <label className="text-muted-foreground font-medium capitalize">{zone.type.replace('_', ' ')}</label>
                            <button
                              onClick={() => {
                                setClosetZone(zone.type as any);
                                setClosetOpen(true);
                              }}
                              className="text-xs px-1.5 py-0.5 rounded bg-muted/50 hover:bg-primary/20 text-foreground transition-colors"
                            >
                              🛍️
                            </button>
                          </div>
                          
                          {/* Garment Selector */}
                          <Select
                            value={zone.garment || ''}
                            onValueChange={(garmentName) =>
                              updateActor(actor.id, {
                                clothing: actor.clothing?.map((z) =>
                                  z.id === zone.id 
                                    ? { ...z, garment: garmentName || undefined, color: availableColors[0] || zone.color }
                                    : z
                                ),
                              })
                            }
                          >
                            <SelectTrigger className="h-7 text-xs w-full">
                              <SelectValue placeholder="Select garment" />
                            </SelectTrigger>
                            <SelectContent>
                              {availableGarments.map((garment) => (
                                <SelectItem key={garment.id} value={garment.name}>
                                  {garment.name}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>

                          {/* Color Selector */}
                          {availableColors.length > 0 && (
                            <Select
                              value={zone.color || ''}
                              onValueChange={(color) =>
                                updateActor(actor.id, {
                                  clothing: actor.clothing?.map((z) =>
                                    z.id === zone.id ? { ...z, color: color || undefined } : z
                                  ),
                                })
                              }
                            >
                              <SelectTrigger className="h-7 text-xs w-full">
                                <SelectValue placeholder="Select color" />
                              </SelectTrigger>
                              <SelectContent>
                                {availableColors.map((color) => (
                                  <SelectItem key={color} value={color}>
                                    {color}
                                  </SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                          )}

                          {/* Material and Fit Selector */}
                          <div className="grid grid-cols-2 gap-1.5">
                            <Select
                              value={zone.material || ''}
                              onValueChange={(material) =>
                                updateActor(actor.id, {
                                  clothing: actor.clothing?.map((z) =>
                                    z.id === zone.id ? { ...z, material: material || undefined } : z
                                  ),
                                })
                              }
                            >
                              <SelectTrigger className="h-7 text-[11px] px-2 w-full">
                                <SelectValue placeholder="Material" />
                              </SelectTrigger>
                              <SelectContent>
                                <SelectItem value="cotton">Cotton</SelectItem>
                                <SelectItem value="leather">Leather</SelectItem>
                                <SelectItem value="denim">Denim</SelectItem>
                                <SelectItem value="silk">Silk</SelectItem>
                                <SelectItem value="wool">Wool</SelectItem>
                                <SelectItem value="polyester">Polyester</SelectItem>
                              </SelectContent>
                            </Select>

                            <Select
                              value={zone.fit || ''}
                              onValueChange={(fit) =>
                                updateActor(actor.id, {
                                  clothing: actor.clothing?.map((z) =>
                                    z.id === zone.id ? { ...z, fit: fit || undefined } : z
                                  ),
                                })
                              }
                            >
                              <SelectTrigger className="h-7 text-[11px] px-2 w-full">
                                <SelectValue placeholder="Fit" />
                              </SelectTrigger>
                              <SelectContent>
                                <SelectItem value="regular">Regular</SelectItem>
                                <SelectItem value="tailored">Tailored</SelectItem>
                                <SelectItem value="oversized">Oversized</SelectItem>
                                <SelectItem value="slim">Slim</SelectItem>
                                <SelectItem value="loose">Loose</SelectItem>
                              </SelectContent>
                            </Select>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>

            {/* 5. POSE & GAZE PANEL */}
            <div className="border border-border rounded-lg overflow-hidden bg-card">
              <button
                onClick={() => toggleSection('pose')}
                className="w-full p-2 bg-muted/30 hover:bg-muted/50 flex items-center justify-between text-xs font-bold text-foreground select-none transition-colors"
              >
                <span>🏃 POSE & GAZE</span>
                <span className="text-[10px]">{expandedSections.pose ? '▼' : '▶'}</span>
              </button>
              {expandedSections.pose && (
                <div className="p-3 border-t border-border space-y-2">
                  <div className="space-y-2">
                    <Select
                      value={actor.pose?.posture || 'Standing'}
                      onValueChange={(value) =>
                        updateActor(actor.id, {
                          pose: { ...actor.pose, posture: value || undefined },
                        })
                      }
                    >
                      <SelectTrigger className="h-7 text-xs w-full">
                        <SelectValue placeholder="Posture" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="Standing">Standing</SelectItem>
                        <SelectItem value="Sitting">Sitting</SelectItem>
                        <SelectItem value="Kneeling">Kneeling</SelectItem>
                        <SelectItem value="Lying">Lying</SelectItem>
                      </SelectContent>
                    </Select>

                    <Select
                      value={actor.pose?.gaze || 'Toward Camera'}
                      onValueChange={(value) =>
                        updateActor(actor.id, {
                          pose: { ...actor.pose, gaze: value || undefined },
                        })
                      }
                    >
                      <SelectTrigger className="h-7 text-xs w-full">
                        <SelectValue placeholder="Gaze" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="Toward Camera">Toward Camera</SelectItem>
                        <SelectItem value="Away">Away</SelectItem>
                        <SelectItem value="Down">Down</SelectItem>
                        <SelectItem value="Up">Up</SelectItem>
                      </SelectContent>
                    </Select>

                    <Select
                      value={actor.pose?.arms || ''}
                      onValueChange={(value) =>
                        updateActor(actor.id, {
                          pose: { ...actor.pose, arms: value || undefined },
                        })
                      }
                    >
                      <SelectTrigger className="h-7 text-xs w-full">
                        <SelectValue placeholder="Arm position" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="at_side">At side</SelectItem>
                        <SelectItem value="crossed">Crossed</SelectItem>
                        <SelectItem value="raised">Raised</SelectItem>
                        <SelectItem value="behind_back">Behind back</SelectItem>
                      </SelectContent>
                    </Select>

                    <Select
                      value={actor.pose?.legs || ''}
                      onValueChange={(value) =>
                        updateActor(actor.id, {
                          pose: { ...actor.pose, legs: value || undefined },
                        })
                      }
                    >
                      <SelectTrigger className="h-7 text-xs w-full">
                        <SelectValue placeholder="Leg position" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="standing">Standing</SelectItem>
                        <SelectItem value="apart">Apart</SelectItem>
                        <SelectItem value="crossed">Crossed</SelectItem>
                        <SelectItem value="bent">Bent</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              )}
            </div>

            {/* 6. RELATIONSHIPS PANEL */}
            <div className="border border-border rounded-lg overflow-hidden bg-card">
              <button
                onClick={() => toggleSection('relationships')}
                className="w-full p-2 bg-muted/30 hover:bg-muted/50 flex items-center justify-between text-xs font-bold text-foreground select-none transition-colors"
              >
                <span>🤝 RELATIONSHIPS</span>
                <span className="text-[10px]">{expandedSections.relationships ? '▼' : '▶'}</span>
              </button>
              {expandedSections.relationships && (
                <div className="p-3 border-t border-border space-y-2">
                  {actor.relationships && actor.relationships.length > 0 ? (
                    <div className="space-y-3">
                      {actor.relationships.map((rel) => {
                        // All potential targets in the scene
                        const allTargets = [
                          ...scene.actors.filter(a => a.id !== actor.id).map(a => ({ id: a.id, name: `👤 ${a.name}`, category: 'human' as const })),
                          ...scene.props.map(p => ({ id: p.id, name: p.category === 'object' ? `📦 ${p.label}` : `🏗️ ${p.label}`, category: p.category || 'fixture' }))
                        ];

                        const currentTargetId = rel.targetPropId || "";
                        const currentTarget = allTargets.find(t => t.id === currentTargetId);
                        const targetCategory = currentTarget ? currentTarget.category : null;

                        return (
                          <div key={rel.id} className="p-2 bg-muted/40 rounded border border-border space-y-2 relative">
                            {/* Remove button */}
                            <button
                              onClick={() => {
                                const updatedRels = (actor.relationships || []).filter((r) => r.id !== rel.id);
                                updateActor(actor.id, { relationships: updatedRels });
                              }}
                              className="absolute top-1 right-1 text-muted-foreground hover:text-destructive text-xs font-bold w-4 h-4 flex items-center justify-center rounded-full hover:bg-muted"
                            >
                              ✕
                            </button>

                            {/* Target Dropdown (Selected first) */}
                            <div className="space-y-1">
                              <label className="text-[10px] text-muted-foreground font-bold uppercase">Target</label>
                              {allTargets.length > 0 ? (
                                <Select
                                  value={currentTargetId}
                                  onValueChange={(val) => {
                                    const newTarget = allTargets.find(t => t.id === val);
                                    let newType: any = '';
                                    if (newTarget) {
                                      if (newTarget.category === 'object') {
                                        newType = 'holding';
                                      } else if (newTarget.category === 'fixture') {
                                        newType = 'leaning_on';
                                      } else if (newTarget.category === 'human') {
                                        newType = 'kneeling_before';
                                      }
                                    }
                                    const updatedRels = (actor.relationships || []).map((r) =>
                                      r.id === rel.id ? { ...r, targetPropId: val, type: newType } : r
                                    );
                                    updateActor(actor.id, { relationships: updatedRels });
                                  }}
                                >
                                  <SelectTrigger className="h-7 text-xs w-full">
                                    <SelectValue placeholder="Select target" />
                                  </SelectTrigger>
                                  <SelectContent>
                                    {allTargets.map((t) => (
                                      <SelectItem key={t.id} value={t.id}>
                                        {t.name}
                                      </SelectItem>
                                    ))}
                                  </SelectContent>
                                </Select>
                              ) : (
                                <div className="text-xs text-muted-foreground italic py-1">
                                  No valid targets available. Add entities first.
                                </div>
                              )}
                            </div>

                            {/* Relationship Type / Action Type (Disabled until Target selected) */}
                            <div className="space-y-1">
                              <label className="text-[10px] text-muted-foreground font-bold uppercase">Action Type</label>
                              <Select
                                value={rel.type}
                                disabled={!currentTargetId}
                                onValueChange={(val: any) => {
                                  const updatedRels = (actor.relationships || []).map((r) =>
                                    r.id === rel.id ? { ...r, type: val, subjects: val === "framing" ? [actor.id] : undefined } : r
                                  );
                                  updateActor(actor.id, { relationships: updatedRels });
                                }}
                              >
                                <SelectTrigger className="h-7 text-xs w-full">
                                  <SelectValue placeholder={currentTargetId ? "Select action" : "Select a target first"} />
                                </SelectTrigger>
                                <SelectContent>
                                  {targetCategory === 'object' && (
                                    <>
                                      <SelectGroup>
                                        <SelectLabel className="text-[10px] font-bold text-muted-foreground uppercase px-2 py-1">🎯 Actions for Objects</SelectLabel>
                                        <SelectItem value="holding">Holding</SelectItem>
                                        <SelectItem value="holding_near_eye">Holding Near Eye</SelectItem>
                                      </SelectGroup>
                                      <SelectGroup>
                                        <SelectLabel className="text-[10px] font-bold text-muted-foreground uppercase px-2 py-1">🌐 General Spatial Actions</SelectLabel>
                                        <SelectItem value="standing_next_to">Standing Next To</SelectItem>
                                      </SelectGroup>
                                    </>
                                  )}
                                  {targetCategory === 'fixture' && (
                                    <>
                                      <SelectGroup>
                                        <SelectLabel className="text-[10px] font-bold text-muted-foreground uppercase px-2 py-1">🧱 Actions for Fixtures</SelectLabel>
                                        <SelectItem value="leaning_on">Leaning On</SelectItem>
                                        <SelectItem value="sitting_at">Sitting At</SelectItem>
                                        <SelectItem value="framing">Framing</SelectItem>
                                      </SelectGroup>
                                      <SelectGroup>
                                        <SelectLabel className="text-[10px] font-bold text-muted-foreground uppercase px-2 py-1">🌐 General Spatial Actions</SelectLabel>
                                        <SelectItem value="standing_next_to">Standing Next To</SelectItem>
                                      </SelectGroup>
                                    </>
                                  )}
                                  {targetCategory === 'human' && (
                                    <>
                                      <SelectGroup>
                                        <SelectLabel className="text-[10px] font-bold text-muted-foreground uppercase px-2 py-1">👤 Multi-Actor Actions</SelectLabel>
                                        <SelectItem value="kneeling_before">Kneeling Before</SelectItem>
                                        <SelectItem value="standing_next_to">Standing Next To</SelectItem>
                                      </SelectGroup>
                                    </>
                                  )}
                                </SelectContent>
                              </Select>
                            </div>

                            {/* Extra UI for framing (multi-select of subjects) */}
                            {rel.type === "framing" && (
                              <div className="space-y-1.5 pt-1 border-t border-border/50">
                                <label className="text-[10px] text-muted-foreground font-bold uppercase font-semibold">Framed Subjects</label>
                                <div className="space-y-1 max-h-24 overflow-y-auto p-1.5 bg-background rounded border border-border/50">
                                  {scene.actors.map((act) => {
                                    const isChecked = rel.subjects?.includes(act.id) || false;
                                    return (
                                      <label key={act.id} className="flex items-center gap-1.5 text-[11px] font-medium text-foreground cursor-pointer select-none">
                                        <input
                                          type="checkbox"
                                          checked={isChecked}
                                          onChange={(e) => {
                                            const currentSubjects = rel.subjects || [];
                                            const updatedSubjects = e.target.checked
                                              ? [...currentSubjects, act.id]
                                              : currentSubjects.filter(sid => sid !== act.id);
                                            const updatedRels = (actor.relationships || []).map((r) =>
                                              r.id === rel.id ? { ...r, subjects: updatedSubjects } : r
                                            );
                                            updateActor(actor.id, { relationships: updatedRels });
                                          }}
                                          className="rounded border-gray-300 text-primary focus:ring-primary h-3 w-3"
                                        />
                                        {act.name}
                                      </label>
                                    );
                                  })}
                                </div>
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  ) : (
                    <div className="text-xs text-muted-foreground text-center py-2">No active relationships</div>
                  )}

                  {/* Add Button & Help text */}
                  <div className="space-y-1 pt-1">
                    <Button
                      size="sm"
                      variant="outline"
                      className="w-full text-xs h-7"
                      onClick={() => {
                        const newRel = {
                          id: `rel-${Date.now()}`,
                          type: '' as const,
                          targetPropId: '',
                          subjects: undefined
                        };
                        updateActor(actor.id, {
                          relationships: [...(actor.relationships || []), newRel]
                        });
                      }}
                      disabled={scene.props.length === 0 && scene.actors.length <= 1}
                    >
                      ➕ Add Interaction
                    </Button>
                    {scene.props.length === 0 && scene.actors.length <= 1 && (
                      <p className="text-[10px] text-muted-foreground text-center italic">
                        Add fixtures or objects to target interactions.
                      </p>
                    )}
                  </div>
                </div>
              )}
            </div>

          </div>
        </div>

        {/* Clothing Closet Modal - rendered outside ScrollArea */}
        <ClothingClosetModal
          open={closetOpen}
          onOpenChange={setClosetOpen}
          actor={actor}
          zone={closetZone}
          onSelectGarment={(garment: string, color?: string) => {
            const hasZone = actor.clothing?.some((z) => z.type === closetZone);
            let updatedClothing = [];
            if (hasZone) {
              updatedClothing = actor.clothing?.map((z) =>
                z.type === closetZone
                  ? { ...z, garment, color: color || z.color }
                  : z
              ) || [];
            } else {
              updatedClothing = [
                ...(actor.clothing || []),
                { id: `${closetZone}-${Date.now()}`, type: closetZone, garment, color: color || 'Neutral' }
              ];
            }
            updateActor(actor.id, { clothing: updatedClothing });
          }}
          onApplyEnsemble={(ensemble: any) => {
            const ensembleTypes = Object.keys(ensemble.clothing);
            const updatedClothing = [...(actor.clothing || [])];
            
            ensembleTypes.forEach((type) => {
              const ensembleZone = ensemble.clothing[type];
              const existingIndex = updatedClothing.findIndex((z) => z.type === type);
              if (existingIndex > -1) {
                updatedClothing[existingIndex] = {
                  ...updatedClothing[existingIndex],
                  ...ensembleZone,
                };
              } else {
                updatedClothing.push({
                  id: `${type}-${Date.now()}`,
                  type: type as any,
                  ...ensembleZone,
                });
              }
            });
            
            updateActor(actor.id, { clothing: updatedClothing });
          }}
        />
      </>
    );
  }

  // Prop Inspector
  if (selection.type === 'prop') {
    const prop = scene.props.find((p) => p.id === selection.id);
    if (!prop) return null;

    return (
      <div className="w-80 border-l border-border bg-background flex flex-col h-full">
        {/* Header */}
        <div className="p-3 border-b border-border flex items-center justify-between">
          <h3 className="text-sm font-semibold">🏺 {prop.label}</h3>
          <Button
            size="sm"
            variant="destructive"
            className="h-6 text-xs"
            onClick={() => removeProp(prop.id)}
          >
            Remove
          </Button>
        </div>

        {/* Form Content */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {/* Category Selector */}
          <div className="space-y-2">
            <label className="text-xs font-semibold text-muted-foreground">CATEGORY</label>
            <Select
              value={prop.category || 'fixture'}
              onValueChange={(val: 'fixture' | 'object') => updateProp(prop.id, { category: val, spatialRole: val === 'object' ? undefined : prop.spatialRole })}
            >
              <SelectTrigger className="h-8 text-xs w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="fixture">🏗️ Fixture</SelectItem>
                <SelectItem value="object">📦 Object</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Type Selector */}
          <div className="space-y-2">
            <label className="text-xs font-semibold text-muted-foreground">TYPE</label>
            <Input
              value={prop.type}
              onChange={(e) => updateProp(prop.id, { type: e.target.value })}
              className="h-8 text-xs"
              placeholder="Prop type"
            />
          </div>

          {/* Label */}
          <div className="space-y-2">
            <label className="text-xs font-semibold text-muted-foreground">LABEL</label>
            <Input
              value={prop.label}
              onChange={(e) => updateProp(prop.id, { label: e.target.value })}
              className="h-8 text-xs"
              placeholder="Label"
            />
          </div>

          {/* Details */}
          <div className="space-y-2">
            <label className="text-xs font-semibold text-muted-foreground">DETAILS</label>
            <textarea
              value={prop.details || ''}
              onChange={(e) => updateProp(prop.id, { details: e.target.value })}
              className="w-full h-20 text-xs p-2 border border-border rounded resize-none"
              placeholder="Details about this prop..."
            />
          </div>

          {/* Material */}
          <div className="space-y-2">
            <label className="text-xs font-semibold text-muted-foreground">MATERIAL</label>
            <Input
              value={prop.material || ''}
              onChange={(e) => updateProp(prop.id, { material: e.target.value })}
              className="h-8 text-xs"
              placeholder="e.g. wood, stone, metal"
            />
          </div>

          {/* Color */}
          <div className="space-y-2">
            <label className="text-xs font-semibold text-muted-foreground">COLOR</label>
            <Input
              value={prop.color || ''}
              onChange={(e) => updateProp(prop.id, { color: e.target.value })}
              className="h-8 text-xs"
              placeholder="e.g. brown, white, gold"
            />
          </div>

          {/* Shape */}
          <div className="space-y-2">
            <label className="text-xs font-semibold text-muted-foreground">SHAPE</label>
            <Input
              value={prop.shape || ''}
              onChange={(e) => updateProp(prop.id, { shape: e.target.value })}
              className="h-8 text-xs"
              placeholder="e.g. round, square"
            />
          </div>

          {/* Spatial Role (Fixtures only) */}
          {(prop.category === 'fixture' || !prop.category) && (
            <div className="space-y-2">
              <label className="text-xs font-semibold text-muted-foreground">SPATIAL ROLE</label>
              <Select
                value={prop.spatialRole || ''}
                onValueChange={(val: any) => updateProp(prop.id, { spatialRole: val || undefined })}
              >
                <SelectTrigger className="h-8 text-xs w-full">
                  <SelectValue placeholder="Select spatial role" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="Boundary">Boundary (e.g. wall)</SelectItem>
                  <SelectItem value="Surface">Surface (e.g. table, desk)</SelectItem>
                  <SelectItem value="Anchor">Anchor (e.g. chair, bench)</SelectItem>
                  <SelectItem value="Frame">Frame (e.g. arch, doorway)</SelectItem>
                </SelectContent>
              </Select>
            </div>
          )}
        </div>
      </div>
    );
  }

  // Atmosphere Inspector
  if (selection.type === 'atmosphere') {
    const atm = scene.atmosphere;

    return (
      <div className="w-80 border-l border-border bg-background flex flex-col h-full">
        {/* Header */}
        <div className="p-3 border-b border-border">
          <h3 className="text-sm font-semibold">🌍 ATMOSPHERE</h3>
        </div>

        {/* Form Content */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {/* Preset Selector */}
          <div className="space-y-2">
            <label className="text-xs font-semibold text-muted-foreground">PRESET</label>
            <Select
              value={atm.preset}
              onValueChange={(val) => {
                const selected = atmospheres.find(a => a.preset === val);
                if (selected) {
                  updateAtmosphere({
                    preset: selected.preset,
                    ground: selected.ground,
                    envelope: selected.envelope,
                    vista: selected.vista,
                    background: selected.background
                  });
                } else {
                  updateAtmosphere({ preset: val || undefined });
                }
              }}
            >
              <SelectTrigger className="h-8 text-xs w-full">
                <SelectValue placeholder="Select preset" />
              </SelectTrigger>
              <SelectContent>
                {atmospheres.map((item) => (
                  <SelectItem key={item.preset} value={item.preset}>
                    {item.icon} {item.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Ground */}
          <div className="space-y-2">
            <label className="text-xs font-semibold text-muted-foreground">GROUND</label>
            <Input
              value={atm.ground || ''}
              onChange={(e) => updateAtmosphere({ ground: e.target.value })}
              className="h-8 text-xs"
              placeholder="Ground description"
            />
          </div>

          {/* Envelope */}
          <div className="space-y-2">
            <label className="text-xs font-semibold text-muted-foreground">ENVELOPE (Lighting)</label>
            <Input
              value={atm.envelope || ''}
              onChange={(e) => updateAtmosphere({ envelope: e.target.value })}
              className="h-8 text-xs"
              placeholder="Lighting/Weather"
            />
          </div>

          {/* Vista */}
          <div className="space-y-2">
            <label className="text-xs font-semibold text-muted-foreground">VISTA (Background)</label>
            <Input
              value={atm.vista || ''}
              onChange={(e) => updateAtmosphere({ vista: e.target.value })}
              className="h-8 text-xs"
              placeholder="Distant background"
            />
          </div>

          {/* Background Detail */}
          <div className="space-y-2">
            <label className="text-xs font-semibold text-muted-foreground">BACKGROUND (Optional)</label>
            <Input
              value={atm.background || ''}
              onChange={(e) => updateAtmosphere({ background: e.target.value })}
              className="h-8 text-xs"
              placeholder="Optional details"
            />
          </div>
        </div>
      </div>
    );
  }

  // Camera Inspector
  if (selection.type === 'camera') {
    const cam = scene.camera;

    return (
      <div className="w-80 border-l border-border bg-background flex flex-col h-full">
        {/* Header */}
        <div className="p-3 border-b border-border">
          <h3 className="text-sm font-semibold">📷 CAMERA & STYLE</h3>
        </div>

        {/* Form Content */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {/* Framing */}
          <div className="space-y-2">
            <label className="text-xs font-semibold text-muted-foreground">FRAMING</label>
            <Select value={cam.framing || 'Medium'} onValueChange={(value) => updateCamera({ framing: value || undefined })}>
              <SelectTrigger className="h-8 text-xs w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="Close-up">Close-up</SelectItem>
                <SelectItem value="Medium">Medium</SelectItem>
                <SelectItem value="Full-body">Full-body</SelectItem>
                <SelectItem value="Wide">Wide</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Angle */}
          <div className="space-y-2">
            <label className="text-xs font-semibold text-muted-foreground">ANGLE</label>
            <Select value={cam.angle || 'Eye-level'} onValueChange={(value) => updateCamera({ angle: value || undefined })}>
              <SelectTrigger className="h-8 text-xs w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="Eye-level">Eye-level</SelectItem>
                <SelectItem value="Low-angle">Low-angle</SelectItem>
                <SelectItem value="High-angle">High-angle</SelectItem>
                <SelectItem value="Dutch">Dutch</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Depth of Field */}
          <div className="space-y-2">
            <label className="text-xs font-semibold text-muted-foreground">DEPTH OF FIELD</label>
            <Select
              value={cam.depthOfField || 'Shallow'}
              onValueChange={(value) => updateCamera({ depthOfField: value || undefined })}
            >
              <SelectTrigger className="h-8 text-xs w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="Shallow">Shallow</SelectItem>
                <SelectItem value="Medium">Medium</SelectItem>
                <SelectItem value="Deep">Deep</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Profile */}
          <div className="space-y-2">
            <label className="text-xs font-semibold text-muted-foreground">RENDER PROFILE</label>
            <Select
              value={cam.renderProfile || 'Cinematic'}
              onValueChange={(value) => updateCamera({ renderProfile: value || undefined })}
            >
              <SelectTrigger className="h-8 text-xs w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="Cinematic">Cinematic</SelectItem>
                <SelectItem value="Natural">Natural</SelectItem>
                <SelectItem value="Stylized">Stylized</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Mood */}
          <div className="space-y-2">
            <label className="text-xs font-semibold text-muted-foreground">MOOD</label>
            <Select value={cam.mood || 'Neutral'} onValueChange={(value) => updateCamera({ mood: value || undefined })}>
              <SelectTrigger className="h-8 text-xs w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="Neutral">Neutral</SelectItem>
                <SelectItem value="Dramatic">Dramatic</SelectItem>
                <SelectItem value="Romantic">Romantic</SelectItem>
                <SelectItem value="Dark">Dark</SelectItem>
                <SelectItem value="Bright">Bright</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
      </div>
    );
  }

  return null;
}
