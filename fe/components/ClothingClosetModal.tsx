'use client';

import React, { useState } from 'react';
import { mockEnsemblesDetailed, mockGarments } from '@/lib/mock-data';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Input } from '@/components/ui/input';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogClose,
} from '@/components/ui/dialog';
import { ActorState } from '@/lib/types';

interface ClothingClosetModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  actor: ActorState;
  zone: 'upper_body' | 'lower_body' | 'feet' | 'hands' | 'headwear';
  onSelectGarment: (garment: string, color?: string) => void;
  onApplyEnsemble: (ensemble: any) => void;
}

export function ClothingClosetModal({
  open,
  onOpenChange,
  actor,
  zone,
  onSelectGarment,
  onApplyEnsemble,
}: ClothingClosetModalProps) {
  const [searchQuery, setSearchQuery] = useState('');

  const garmentOptions = mockGarments[zone as keyof typeof mockGarments] || [];
  const currentZoneClothing = actor.clothing?.find((c) => c.type === zone);

  const handleGarmentSelect = (garment: string) => {
    onSelectGarment(garment);
    onOpenChange(false);
  };

  const handleEnsembleApply = (ensemble: any) => {
    onApplyEnsemble(ensemble);
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[90vh] flex flex-col">
        <DialogHeader>
          <div className="flex items-center justify-between w-full">
            <DialogTitle className="text-lg font-bold">
              🛍️ Clothing Closet — {actor.name} — {zone.replace('_', ' ').toUpperCase()}
            </DialogTitle>
            <DialogClose />
          </div>
        </DialogHeader>

        <Tabs defaultValue="ensembles" className="flex-1 flex flex-col overflow-hidden">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="ensembles">📁 Ensembles (Full Outfit)</TabsTrigger>
            <TabsTrigger value="singles">👕 Singles (Pick One)</TabsTrigger>
          </TabsList>

          {/* Ensembles Tab */}
          <TabsContent value="ensembles" className="flex-1 overflow-hidden m-0 flex flex-col">
            <ScrollArea className="flex-1">
              <div className="p-4 space-y-3">
                <div className="text-sm text-muted-foreground mb-3">
                  Apply a complete outfit to all clothing zones at once
                </div>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                  {mockEnsemblesDetailed.map((ensemble) => (
                    <div
                      key={ensemble.id}
                      className="p-3 border border-border rounded-lg bg-muted/30 hover:bg-muted/60 transition-colors flex flex-col gap-2"
                    >
                      <div className="text-3xl text-center">{ensemble.icon}</div>
                      <div>
                        <h4 className="font-semibold text-sm">{ensemble.name}</h4>
                        <p className="text-xs text-muted-foreground">{ensemble.description}</p>
                      </div>
                      <Button
                        size="sm"
                        variant="default"
                        className="w-full text-xs"
                        onClick={() => handleEnsembleApply(ensemble)}
                      >
                        Apply to All Zones
                      </Button>
                    </div>
                  ))}
                </div>
              </div>
            </ScrollArea>
          </TabsContent>

          {/* Singles Tab */}
          <TabsContent value="singles" className="flex-1 overflow-hidden m-0 flex flex-col">
            <div className="p-3 border-b border-border">
              <Input
                placeholder="Search garments..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="h-8 text-sm"
              />
            </div>
            <ScrollArea className="flex-1">
              <div className="p-4">
                <div className="text-sm text-muted-foreground mb-3">
                  Select a garment for {zone.replace('_', ' ')}
                </div>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                  {garmentOptions
                    .filter((g) => g.name.toLowerCase().includes(searchQuery.toLowerCase()))
                    .map((garment) => (
                      <div
                        key={garment.id}
                        className={`p-3 border rounded-lg transition-all cursor-pointer ${
                          currentZoneClothing?.garment === garment.name
                            ? 'border-primary bg-primary/10'
                            : 'border-border bg-muted/30 hover:bg-muted/60'
                        }`}
                      >
                        <h4 className="font-semibold text-sm mb-2">{garment.name}</h4>
                        <div className="mb-2 space-y-1">
                          {garment.colors.map((color) => (
                            <button
                              key={color}
                              onClick={() => handleGarmentSelect(garment.name)}
                              className="block w-full text-xs px-2 py-1 rounded bg-background/80 hover:bg-background border border-border/50 text-left"
                            >
                              <span className="inline-block w-2 h-2 rounded-full mr-1 bg-gray-400"></span>
                              {color}
                            </button>
                          ))}
                        </div>
                        <Button
                          size="sm"
                          variant={
                            currentZoneClothing?.garment === garment.name ? 'default' : 'outline'
                          }
                          className="w-full text-xs"
                          onClick={() => handleGarmentSelect(garment.name)}
                        >
                          {currentZoneClothing?.garment === garment.name ? '✓ Selected' : 'Select'}
                        </Button>
                      </div>
                    ))}
                </div>
              </div>
            </ScrollArea>
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  );
}
