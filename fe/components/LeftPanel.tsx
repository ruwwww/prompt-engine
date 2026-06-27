'use client';

import React, { useState } from 'react';
import { mockArchetypes, mockAtmospheres, mockProps } from '@/lib/mock-data';
import { useScene } from '@/lib/scene-context';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ScrollArea } from '@/components/ui/scroll-area';
import { ActorState, PropState } from '@/lib/types';

export function LeftPanel() {
  const { scene, ui, setSelection, addActor, addProp, addGroup, updateAtmosphere, catalog } = useScene();
  const [searchQuery, setSearchQuery] = useState('');

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

  const handleAddArchetype = (archetypeId: string) => {
    const archetype = archetypes.find((a) => a.id === archetypeId);
    if (!archetype) return;

    const preset = catalog?.subjects?.[archetypeId] || {};
    
    // Parse face expression
    const expression = preset.Face?.expression 
      ? preset.Face.expression.charAt(0).toUpperCase() + preset.Face.expression.slice(1)
      : 'Neutral';

    // Parse hair style, color, length
    const hairStyle = preset.Hair?.style 
      ? preset.Hair.style.charAt(0).toUpperCase() + preset.Hair.style.slice(1)
      : 'Straight';
    const hairColor = preset.Hair?.color 
      ? preset.Hair.color.charAt(0).toUpperCase() + preset.Hair.color.slice(1)
      : 'Brown';
    const hairLength = preset.Hair?.length 
      ? preset.Hair.length.charAt(0).toUpperCase() + preset.Hair.length.slice(1)
      : 'Medium';

    // Parse clothing zones from preset owned items
    const clothing: any[] = [];
    const zones = [
      { key: 'UpperBody', type: 'upper_body', defaultGarment: 'Shirt', defaultColor: 'White' },
      { key: 'LowerBody', type: 'lower_body', defaultGarment: 'Pants', defaultColor: 'Blue' },
      { key: 'Feet', type: 'feet', defaultGarment: 'Shoes', defaultColor: 'Black' },
      { key: 'Hands', type: 'hands', defaultGarment: '', defaultColor: '' },
      { key: 'Headwear', type: 'headwear', defaultGarment: '', defaultColor: '' }
    ];

    zones.forEach(z => {
      if (preset[z.key]) {
        const itemId = preset[z.key].owned_item_id || '';
        // Clean up "hoodie_1" -> "Hoodie"
        let garmentName = itemId.split('_')[0];
        if (garmentName) {
          garmentName = garmentName.charAt(0).toUpperCase() + garmentName.slice(1);
        }
        clothing.push({
          id: `${z.type}-${Date.now()}-${Math.random().toString().slice(-4)}`,
          type: z.type,
          garment: garmentName || z.defaultGarment,
          color: z.defaultColor || 'Neutral'
        });
      } else {
        clothing.push({
          id: `${z.type}-${Date.now()}-${Math.random().toString().slice(-4)}`,
          type: z.type,
          garment: '',
          color: ''
        });
      }
    });

    const actorCount = scene.actors.length + 1;
    const actorSlug = archetypeId.toLowerCase().replace(/[^a-z0-9]+/g, '-');
    let actorId = `actor-${actorCount}-${actorSlug}`;
    let actorIndex = 1;
    while (scene.actors.some(a => a.id === actorId)) {
      actorId = `actor-${actorCount}-${actorSlug}-${actorIndex}`;
      actorIndex++;
    }

    let actorName = archetype.name;
    let actorNameIndex = 1;
    while (scene.actors.some(a => a.name === actorName)) {
      actorName = `${archetype.name} ${actorNameIndex + 1}`;
      actorNameIndex++;
    }

    const newActor: ActorState = {
      id: actorId,
      name: actorName,
      archetype: archetypeId,
      gender: preset.gender || (archetypeId.includes('woman') || archetypeId.includes('influencer') ? 'woman' : 'man'),
      face: { expression },
      hair: {
        style: hairStyle,
        color: hairColor,
        length: hairLength,
      },
      clothing,
      pose: {
        posture: 'Standing',
        gaze: 'Toward Camera',
      },
      relationships: [],
    };

    addActor(newActor);
  };

  const handleAddProp = (propId: string) => {
    const prop = mockProps.find((p) => p.id === propId);
    if (!prop) return;

    const propCount = scene.props.length + 1;
    const propSlug = prop.type.toLowerCase().replace(/[^a-z0-9]+/g, '-');
    let generatedPropId = `prop-${propCount}-${propSlug}`;
    let propIndex = 1;
    while (scene.props.some(p => p.id === generatedPropId)) {
      generatedPropId = `prop-${propCount}-${propSlug}-${propIndex}`;
      propIndex++;
    }

    const newProp: PropState = {
      id: generatedPropId,
      category: prop.category || 'fixture',
      type: prop.type,
      label: prop.label,
      details: prop.details,
    };

    addProp(newProp);
  };

  const filteredArchetypes = archetypes.filter(a => 
    a.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const filteredAtmospheres = atmospheres.filter(a => 
    a.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const filteredProps = mockProps.filter(p => 
    p.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="w-56 border-r border-border bg-background flex flex-col h-full divide-y divide-border">
      {/* 📋 Upper Section: Outliner / Scene Hierarchy */}
      <div className="flex-1 flex flex-col min-h-0">
        <div className="p-2 border-b border-border bg-muted/20 font-bold text-xs text-foreground uppercase tracking-wider select-none">
          📋 Scene Outliner
        </div>
        <ScrollArea className="flex-1">
          <div className="p-3 space-y-3">
            {/* Scene Title */}
            <div className="text-xs font-semibold text-muted-foreground">
              SCENE: {scene.name}
            </div>

            {/* Actors Section */}
            <div className="space-y-1">
              <div className="text-xs font-semibold text-foreground flex items-center gap-1">
                👤 Actors ({scene.actors.length})
              </div>
              {scene.actors.length === 0 ? (
                <div className="text-[11px] text-muted-foreground ml-2 py-0.5">No actors in scene</div>
              ) : (
                <div className="ml-2 space-y-1">
                  {scene.actors.map((actor) => (
                    <button
                      key={actor.id}
                      onClick={() => setSelection('actor', actor.id)}
                      className={`w-full text-left text-xs px-2 py-1 rounded transition-colors ${
                        ui.selection.type === 'actor' && ui.selection.id === actor.id
                          ? 'bg-primary text-primary-foreground'
                          : 'hover:bg-muted'
                      }`}
                    >
                      👤 {actor.name}
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Social Groups Section */}
            <div className="space-y-1 pt-1">
              <div className="text-[11px] font-semibold text-foreground flex items-center gap-1">
                👥 Social Groups ({(scene.groups || []).length})
                <button
                  onClick={() => addGroup({
                    id: `group_${Date.now()}`,
                    type: 'couple',
                    members: []
                  })}
                  className="ml-auto text-[10px] text-primary hover:underline font-normal select-none"
                >
                  ➕ Add
                </button>
              </div>
              {(!scene.groups || scene.groups.length === 0) ? (
                <div className="text-[11px] text-muted-foreground ml-2 py-0.5">No social groups</div>
              ) : (
                <div className="ml-2 space-y-1">
                  {scene.groups.map((group) => (
                    <button
                      key={group.id}
                      onClick={() => setSelection('group', group.id)}
                      className={`w-full text-left text-[11px] px-2 py-1 rounded transition-colors truncate ${
                        ui.selection.type === 'group' && ui.selection.id === group.id
                          ? 'bg-primary text-primary-foreground font-semibold'
                          : 'hover:bg-muted text-muted-foreground hover:text-foreground'
                      }`}
                    >
                      👥 {group.label || `${group.type.charAt(0).toUpperCase() + group.type.slice(1)}`} ({group.members.length} members)
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Props Section */}
            <div className="space-y-1 pt-1">
              <div className="text-[11px] font-semibold text-foreground flex items-center gap-1">
                🏺 Props ({scene.props.length})
                <span className="text-[10px] text-muted-foreground font-normal ml-auto">
                  {scene.props.filter(p => p.category === 'fixture' || !p.category).length}🏗️ | {scene.props.filter(p => p.category === 'object').length}📦
                </span>
              </div>
              {scene.props.length === 0 ? (
                <div className="text-[11px] text-muted-foreground ml-2 py-0.5">No props in scene</div>
              ) : (
                <div className="ml-2 space-y-1">
                  {scene.props.map((prop) => (
                    <button
                      key={prop.id}
                      onClick={() => setSelection('prop', prop.id)}
                      className={`w-full text-left text-[11px] px-2 py-1 rounded transition-colors truncate ${
                        ui.selection.type === 'prop' && ui.selection.id === prop.id
                          ? 'bg-primary text-primary-foreground'
                          : 'hover:bg-muted text-muted-foreground hover:text-foreground'
                      }`}
                    >
                      {prop.category === 'object' ? '📦' : '🏗️'} {prop.label}
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Atmosphere Trigger */}
            <div className="pt-1">
              <button
                onClick={() => setSelection('atmosphere', scene.atmosphere.id)}
                className={`w-full text-left text-xs px-2 py-1 rounded font-semibold transition-colors ${
                  ui.selection.type === 'atmosphere'
                    ? 'bg-primary text-primary-foreground'
                    : 'hover:bg-muted'
                }`}
              >
                🌍 Atmosphere: {scene.atmosphere.preset}
              </button>
            </div>

            {/* Camera Trigger */}
            <div className="pt-1">
              <button
                onClick={() => setSelection('camera', scene.camera.id)}
                className={`w-full text-left text-xs px-2 py-1 rounded font-semibold transition-colors ${
                  ui.selection.type === 'camera'
                    ? 'bg-primary text-primary-foreground'
                    : 'hover:bg-muted'
                }`}
              >
                📷 Camera & Style
              </button>
            </div>
          </div>
        </ScrollArea>
      </div>

      {/* 🗂️ Lower Section: Asset Library */}
      <div className="flex-1 flex flex-col min-h-0">
        <div className="p-2 border-b border-border bg-muted/20 font-bold text-xs text-foreground uppercase tracking-wider select-none">
          🗂️ Asset Library
        </div>

        {/* Filter Input */}
        <div className="p-2 border-b border-border">
          <Input
            placeholder="Search assets..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="h-7 text-xs"
          />
        </div>

        {/* Categories Tab list */}
        <Tabs defaultValue="archetypes" className="flex-1 flex flex-col overflow-hidden">
          <TabsList className="w-full rounded-none border-b border-border bg-background h-auto p-1 gap-1">
            <TabsTrigger value="archetypes" className="text-[11px] py-1 px-2 flex-1">
              👤 Actors
            </TabsTrigger>
            <TabsTrigger value="atmospheres" className="text-[11px] py-1 px-2 flex-1">
              🌍 Atmosphere
            </TabsTrigger>
            <TabsTrigger value="props" className="text-[11px] py-1 px-2 flex-1">
              🏺 Props
            </TabsTrigger>
          </TabsList>

          {/* Archetypes list */}
          <TabsContent value="archetypes" className="flex-1 overflow-hidden m-0 p-0">
            <ScrollArea className="w-full h-full">
              <div className="grid grid-cols-2 gap-1 p-2">
                {filteredArchetypes.map((archetype) => (
                  <div
                    key={archetype.id}
                    className="p-1.5 border border-border rounded bg-muted/30 hover:bg-muted/60 transition-colors"
                  >
                    <div className="text-xl text-center mb-0.5">{archetype.icon}</div>
                    <p className="text-[11px] font-medium text-center mb-1.5 truncate">{archetype.name}</p>
                    <Button
                      size="sm"
                      variant="outline"
                      className="w-full text-xs h-6 py-0"
                      onClick={() => handleAddArchetype(archetype.id)}
                    >
                      Add
                    </Button>
                  </div>
                ))}
              </div>
            </ScrollArea>
          </TabsContent>

          {/* Atmospheres list */}
          <TabsContent value="atmospheres" className="flex-1 overflow-hidden m-0 p-0">
            <ScrollArea className="w-full h-full">
              <div className="grid grid-cols-2 gap-1 p-2">
                {filteredAtmospheres.map((atm) => (
                  <div
                    key={atm.id}
                    className="p-1.5 border border-border rounded bg-muted/30 hover:bg-muted/60 transition-colors"
                  >
                    <div className="text-xl text-center mb-0.5">{atm.icon}</div>
                    <p className="text-[11px] font-medium text-center mb-1.5 truncate">{atm.name}</p>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => {
                        updateAtmosphere({
                          preset: atm.preset,
                          ground: atm.ground,
                          envelope: atm.envelope,
                          vista: atm.vista,
                          background: atm.background,
                        });
                        setSelection('atmosphere', scene.atmosphere.id);
                      }}
                    >
                      Select
                    </Button>
                  </div>
                ))}
              </div>
            </ScrollArea>
          </TabsContent>

          {/* Props list */}
          <TabsContent value="props" className="flex-1 overflow-hidden m-0 p-0">
            <ScrollArea className="w-full h-full">
              <div className="grid grid-cols-2 gap-1 p-2">
                {filteredProps.map((prop) => (
                  <div
                    key={prop.id}
                    className="p-1.5 border border-border rounded bg-muted/30 hover:bg-muted/60 transition-colors"
                  >
                    <div className="text-xl text-center mb-0.5">{prop.icon}</div>
                    <p className="text-[11px] font-medium text-center mb-1.5 truncate">{prop.name}</p>
                    <Button
                      size="sm"
                      variant="outline"
                      className="w-full text-xs h-6 py-0"
                      onClick={() => handleAddProp(prop.id)}
                    >
                      Add
                    </Button>
                  </div>
                ))}
              </div>
            </ScrollArea>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
