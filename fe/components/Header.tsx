'use client';

import React, { useRef } from 'react';
import { useScene } from '@/lib/scene-context';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Settings, FileUp } from 'lucide-react';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

export function Header() {
  const { 
    scene, 
    updateSceneName, 
    saveCurrentScene, 
    loadScene, 
    importScene, 
    savedScenesList, 
    resetScene 
  } = useScene();

  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleExport = () => {
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(scene, null, 2));
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute("href", dataStr);
    downloadAnchor.setAttribute("download", `${scene.name.toLowerCase().replace(/\s+/g, '_')}_scene.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  const handleImportClick = () => {
    fileInputRef.current?.click();
  };

  const handleImportFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      try {
        const json = JSON.parse(event.target?.result as string);
        importScene(json);
      } catch (err) {
        alert("Failed to parse JSON file: " + err);
      }
    };
    reader.readAsText(file);
    e.target.value = ''; // Reset file input
  };

  return (
    <header className="h-12 border-b border-border bg-background flex items-center justify-between px-4 gap-4">
      <div className="flex items-center gap-3">
        <span className="text-xl">🎬</span>
        <h1 className="text-sm font-semibold">Prompt Engine Studio</h1>
      </div>

      <Input
        type="text"
        value={scene.name}
        onChange={(e) => updateSceneName(e.target.value)}
        placeholder="Untitled Scene"
        className="max-w-xs text-xs h-8"
      />

      <div className="flex items-center gap-2 ml-auto">
        {/* Load dropdown */}
        <Select value="" onValueChange={(val) => { if (val === 'reset') { resetScene(); } else if (val) { loadScene(val); } }}>
          <SelectTrigger className="h-8 text-xs w-[120px]">
            <SelectValue placeholder="📁 Load Scene" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="reset">📄 [New Scene]</SelectItem>
            {savedScenesList.map((item) => (
              <SelectItem key={item.id} value={item.id}>
                🎬 {item.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Button size="sm" variant="outline" className="text-xs h-8" onClick={saveCurrentScene}>
          💾 Save
        </Button>
        
        <Button size="sm" variant="outline" className="text-xs h-8 gap-1" onClick={handleImportClick}>
          <FileUp className="w-3.5 h-3.5" />
          Import
        </Button>
        <input 
          type="file" 
          ref={fileInputRef} 
          className="hidden" 
          accept=".json" 
          onChange={handleImportFile} 
        />

        <Button size="sm" variant="outline" className="text-xs h-8" onClick={handleExport}>
          📤 Export
        </Button>
        <Button size="sm" variant="ghost" className="text-xs h-8 px-2">
          <Settings className="w-4 h-4" />
        </Button>
      </div>
    </header>
  );
}
