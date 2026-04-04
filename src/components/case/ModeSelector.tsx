"use client";

import type { ChangeEvent } from "react";
import { modeLabels, type AriaMode } from "@/lib/mock-data";
import { useRunStore } from "@/store/runStore";

export default function ModeSelector() {
  const { selectedMode, selectMode } = useRunStore();

  return (
    <div className="rounded-md border border-white/10 bg-white/5 p-3">
      <label htmlFor="mode-select" className="mb-1 block text-xs text-white/60">
        Run Mode
      </label>
      <select
        id="mode-select"
        value={selectedMode}
        onChange={(event: ChangeEvent<HTMLSelectElement>) =>
          selectMode(event.target.value as AriaMode)
        }
        className="w-full rounded-md border border-white/20 bg-[#0d1119] px-2 py-2 text-sm"
      >
        {(Object.keys(modeLabels) as AriaMode[]).map((key) => (
          <option key={key} value={key}>
            {modeLabels[key]}
          </option>
        ))}
      </select>
    </div>
  );
}
