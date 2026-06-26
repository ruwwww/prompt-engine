'use client';

import React, { useState } from 'react';
import { useScene } from '@/lib/scene-context';
import { Button } from '@/components/ui/button';
import { Toggle } from '@/components/ui/toggle';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Copy, Volume2 } from 'lucide-react';

export function CenterPanel() {
  const { scene, setAutoCompile, compileScene } = useScene();
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(scene.promptOutput);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const wordCount = scene.promptOutput.split(/\s+/).filter(w => w.length > 0).length;

  return (
    <div className="flex-1 border-r border-border bg-background flex flex-col h-full">
      {/* Header */}
      <div className="p-2 border-b border-border flex items-center justify-between gap-2 h-11">
        <span className="text-xs font-semibold text-foreground px-2">
          📋 8-Field Prompt Breakdown
        </span>

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

      {/* Content: 8-Field breakdown only */}
      <div className="flex-1 overflow-hidden">
        <ScrollArea className="w-full h-full">
          <div className="p-4 space-y-3">
            {[
              { label: 'Subject', value: scene.eightFieldPrompt.subject },
              { label: 'Clothing', value: scene.eightFieldPrompt.clothing || 'Not specified' },
              { label: 'Action', value: scene.eightFieldPrompt.action || 'Standing' },
              { label: 'Environment', value: scene.eightFieldPrompt.environment },
              { label: 'Lighting', value: scene.eightFieldPrompt.lighting },
              { label: 'Camera', value: scene.eightFieldPrompt.camera },
              { label: 'Style', value: scene.eightFieldPrompt.style },
              { label: 'Composition', value: scene.eightFieldPrompt.composition || 'Balanced' },
            ].map((field) => (
              <div key={field.label} className="space-y-1">
                <label className="text-xs font-semibold text-muted-foreground">
                  {field.label}
                </label>
                <p className="text-sm text-foreground p-2 bg-muted/30 rounded border border-border">
                  {field.value}
                </p>
              </div>
            ))}
          </div>
        </ScrollArea>
      </div>

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
