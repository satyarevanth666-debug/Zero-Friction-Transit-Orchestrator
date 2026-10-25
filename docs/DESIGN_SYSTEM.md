# Design System & UI Specifications

## 1. Visual Language & Tone
- **Aesthetic**: Modern, calm, trustworthy "travel-tech" feel. Lots of white space, soft shadows, rounded corners, subtle gradient accents.
- **Dark & Light Modes**: Seamless switching using Tailwind and CSS variables.

## 2. Color Tokens

### Light Theme
- Background: `#F8FAFC` (`slate-50`)
- Surface: `#FFFFFF` (`white`)
- Surface-2: `#F1F5F9` (`slate-100`)
- Border: `#E2E8F0` (`slate-200`)
- Text: `#0F172A` (`slate-900`)
- Muted: `#64748B` (`slate-500`)

### Dark Theme
- Background: `#0B1020`
- Surface: `#111827` (`gray-900`)
- Surface-2: `#1F2937` (`gray-800`)
- Border: `#263244`
- Text: `#F1F5F9` (`slate-100`)
- Muted: `#94A3B8` (`slate-400`)

### Brand & Accents
- Brand Primary: `#4F46E5` (Indigo-600, Hover: `#4338CA`)
- Brand Accent: `#14B8A6` (Teal-500)
- Status Success: `#10B981` (Emerald-500)
- Status Warning: `#F59E0B` (Amber-500)
- Status Danger: `#F43F5E` (Rose-500)
- Status Info: `#0EA5E9` (Sky-500)

### Mode Colors
- Train: `#4F46E5` (Indigo)
- Bus: `#14B8A6` (Teal)
- Flight: `#0EA5E9` (Sky)
- Transfer / Layover: Slate hatched pattern

## 3. Typography & Spacing
- Primary Font: Inter (UI) with tabular numbers for prices and durations.
- Monospace Font: JetBrains Mono for station codes (e.g. `BZA`, `DMM`).
- Spacing: 8px grid system. Touch targets $\ge 44\text{px}$.
