'use client';

import { SceneProvider } from '@/lib/scene-context';
import { Header } from '@/components/Header';
import { Footer } from '@/components/Footer';
import { LeftPanel } from '@/components/LeftPanel';
import { CenterPanel } from '@/components/CenterPanel';
import { RightPanel } from '@/components/RightPanel';

export default function Page() {
  return (
    <SceneProvider>
      <div className="flex flex-col h-screen bg-background">
        {/* Header */}
        <Header />

        {/* Main Layout (3-Panel) */}
        <div className="flex flex-1 overflow-hidden">
          <LeftPanel />
          <CenterPanel />
          <RightPanel />
        </div>

        {/* Footer */}
        <Footer />
      </div>
    </SceneProvider>
  );
}
