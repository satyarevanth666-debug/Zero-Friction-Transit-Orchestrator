"use client";

export function ThemeToggle() {
  return (
    <div
      id="transit-engine-status"
      className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-blue-50 border border-blue-200 text-blue-700 text-xs font-medium shadow-2xs select-none"
      title="Timetable route planner"
    >
      <span className="inline-flex rounded-full h-2 w-2 bg-blue-500"></span>
      <span className="text-[11px] font-semibold tracking-tight">Route planner</span>
    </div>
  );
}
