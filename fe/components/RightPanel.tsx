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
} from '@/components/ui/select';
import { ScrollArea } from '@/components/ui/scroll-area';
import { mockArchetypes, mockGarments } from '@/lib/mock-data';
import { ClothingClosetModal } from '@/components/ClothingClosetModal';

export function RightPanel() {
  const { scene, ui, selection, updateActor, updateProp, updateAtmosphere, updateCamera, removeActor, removeProp } =
    useScene();

  const [closetOpen, setClosetOpen] = useState(false);
  const [closetZone, setClosetZone] = useState<'upper_body' | 'lower_body' | 'feet' | 'hands' | 'headwear'>('upper_body');

  // No selection - show placeholder
  if (!selection.type || !selection.id) {
    return (
      <div className="w-80 border-l border-border bg-background flex flex-col h-full">
        <div className="p-4 flex items-center justify-center h-full text-center">
          <div className="space-y-2">
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
            <h3 className="text-sm font-semibold">👤 {actor.name}</h3>
            <Button
              size="sm"
              variant="destructive"
              className="h-6 text-xs"
              onClick={() => removeActor(actor.id)}
            >
              Remove
            </Button>
          </div>

          {/* Form Content */}
          <ScrollArea className="flex-1">
            <div className="p-4 space-y-4">
            {/* Archetype Selector */}
            <div className="space-y-2">
              <label className="text-xs font-semibold text-muted-foreground">ARCHETYPE</label>
              <Select
                value={actor.archetype}
                onValueChange={(value) => updateActor(actor.id, { archetype: value || undefined })}
              >
                <SelectTrigger className="h-8 text-xs">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {mockArchetypes.map((arch) => (
                    <SelectItem key={arch.id} value={arch.id}>
                      {arch.icon} {arch.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Face Section */}
            <div className="space-y-2 pt-2">
              <label className="text-xs font-semibold text-muted-foreground">FACE</label>
              <Select
                value={actor.face?.expression || 'Neutral'}
                onValueChange={(value) =>
                  updateActor(actor.id, {
                    face: { ...actor.face, expression: value || undefined },
                  })
                }
              >
                <SelectTrigger className="h-8 text-xs">
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

            {/* Hair Section */}
            <div className="space-y-2 pt-2">
              <label className="text-xs font-semibold text-muted-foreground">HAIR</label>
              <div className="space-y-1.5">
                <Select
                  value={actor.hair?.style || 'Straight'}
                  onValueChange={(value) =>
                    updateActor(actor.id, {
                      hair: { ...actor.hair, style: value || undefined },
                    })
                  }
                >
                  <SelectTrigger className="h-7 text-xs">
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
                  <SelectTrigger className="h-7 text-xs">
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
                  <SelectTrigger className="h-7 text-xs">
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

            {/* Clothing Section */}
            <div className="space-y-2 pt-2">
              <label className="text-xs font-semibold text-muted-foreground">CLOTHING</label>
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
                        <SelectTrigger className="h-7 text-xs">
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
                          <SelectTrigger className="h-7 text-xs">
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
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Pose & Gaze Section */}
            <div className="space-y-2 pt-2">
              <label className="text-xs font-semibold text-muted-foreground">POSE & GAZE</label>
              <div className="space-y-1.5">
                <Select
                  value={actor.pose?.posture || 'Standing'}
                  onValueChange={(value) =>
                    updateActor(actor.id, {
                      pose: { ...actor.pose, posture: value || undefined },
                    })
                  }
                >
                  <SelectTrigger className="h-7 text-xs">
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
                  <SelectTrigger className="h-7 text-xs">
                    <SelectValue placeholder="Gaze" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="Toward Camera">Toward Camera</SelectItem>
                    <SelectItem value="Away">Away</SelectItem>
                    <SelectItem value="Down">Down</SelectItem>
                    <SelectItem value="Up">Up</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            {/* Relationships Section */}
            <div className="space-y-2 pt-2">
              <label className="text-xs font-semibold text-muted-foreground">RELATIONSHIPS</label>
              {actor.relationships && actor.relationships.length > 0 ? (
                <div className="space-y-1.5 text-xs">
                  {actor.relationships.map((rel) => (
                    <div key={rel.id} className="p-2 bg-muted/50 rounded border border-border">
                      <div className="font-medium">{rel.type}</div>
                      {rel.targetPropId && (
                        <div className="text-muted-foreground text-xs">Target: {rel.targetPropId}</div>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-xs text-muted-foreground">No relationships yet</div>
              )}
              <Button size="sm" variant="outline" className="w-full text-xs h-7">
                + Add Interaction
              </Button>
            </div>
          </div>
        </ScrollArea>
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
        <ScrollArea className="flex-1">
          <div className="p-4 space-y-4">
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
          </div>
        </ScrollArea>
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
        <ScrollArea className="flex-1">
          <div className="p-4 space-y-4">
            {/* Preset */}
            <div className="space-y-2">
              <label className="text-xs font-semibold text-muted-foreground">PRESET</label>
              <Input
                value={atm.preset}
                onChange={(e) => updateAtmosphere({ preset: e.target.value })}
                className="h-8 text-xs"
              />
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
        </ScrollArea>
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
        <ScrollArea className="flex-1">
          <div className="p-4 space-y-4">
            {/* Framing */}
            <div className="space-y-2">
              <label className="text-xs font-semibold text-muted-foreground">FRAMING</label>
              <Select value={cam.framing || 'Medium'} onValueChange={(value) => updateCamera({ framing: value || undefined })}>
                <SelectTrigger className="h-8 text-xs">
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
                <SelectTrigger className="h-8 text-xs">
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

            {/* Profile */}
            <div className="space-y-2">
              <label className="text-xs font-semibold text-muted-foreground">RENDER PROFILE</label>
              <Select
                value={cam.renderProfile || 'Cinematic'}
                onValueChange={(value) => updateCamera({ renderProfile: value || undefined })}
              >
                <SelectTrigger className="h-8 text-xs">
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
                <SelectTrigger className="h-8 text-xs">
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
        </ScrollArea>
      </div>
    );
  }

  return null;
}
