"use client";

import { Activity } from "lucide-react";

export function ThemeToggle() {
  return (
    <div
      id="transit-engine-status"
      className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-50/90 border border-emerald-200/90 text-emerald-700 text-xs font-medium shadow-2xs select-none"
      title="RAPTOR timetable engine is active"
    >
      <span className="relative flex h-2 w-2">
        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
        <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
      </span>
      <span className="text-[11px] font-semibold tracking-tight">RAPTOR Live</span>
    </div>
  );
}
