'use client';

import React from 'react';
import { useScene } from '@/lib/scene-context';
import { Button } from '@/components/ui/button';

export function Footer() {
  const { scene, compileScene, resetScene } = useScene();

  const wordCount = scene.promptOutput.split(/\s+/).filter(w => w.length > 0).length;
  const propCount = scene.props?.length || 0;

  return (
    <footer className="h-10 border-t border-border bg-background flex items-center justify-between px-4">
      <div className="text-xs text-muted-foreground">
        Status: ✅ Ready | Actors: {scene.actors.length} | Props: {propCount} | Words: {wordCount}
      </div>

      <div className="flex items-center gap-1">
        <Button
          size="sm"
          variant="outline"
          className="text-xs h-7 gap-1"
          onClick={() => compileScene()}
        >
          ⚡ Compile
        </Button>
        <Button size="sm" variant="outline" className="text-xs h-7 gap-1">
          👁️ Preview
        </Button>
        <Button size="sm" variant="outline" className="text-xs h-7 gap-1">
          📋 Copy
        </Button>
        <Button size="sm" variant="outline" className="text-xs h-7 gap-1">
          💾 Save
        </Button>
        <Button size="sm" variant="outline" className="text-xs h-7 gap-1">
          📤 Export JSON
        </Button>
        <Button
          size="sm"
          variant="outline"
          className="text-xs h-7 gap-1"
          onClick={() => resetScene()}
        >
          ⟳ Reset
        </Button>
      </div>
    </footer>
  );
}
