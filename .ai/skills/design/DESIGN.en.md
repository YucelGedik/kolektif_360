# UI Design System

Read this before UI changes. This file keeps general design rules without
project-specific component names.

## Principles

- Follow the existing design system and component patterns.
- The first screen should show the usable experience, not unnecessary marketing.
- Controls must not overlap, and text must not overflow buttons or cards.
- Prefer existing spacing, theme tokens, and layout helpers over hardcoded pixels.
- Reuse the current palette and typography before adding new visual primitives.

## Layout

- Vertical flow: place new controls after the previous control with consistent spacing.
- For three or more controls in a row or grid, use the framework layout system.
- Define responsive constraints: min/max widths, grid tracks, aspect ratios, or container constraints.
- Do not nest cards inside cards. Use cards for repeated items, modals, or real tool surfaces.

## Control Choice

- Use checkbox/toggle controls for binary settings.
- Use inputs, steppers, or sliders for numeric values.
- Use segmented controls or tabs for modes.
- Use icon buttons for clear commands, with tooltips for unfamiliar icons.
- Use menus/selects for option sets.

## Visual Checklist

- [ ] No text overflow.
- [ ] No incoherent overlap.
- [ ] Hover/focus/disabled/loading states are handled.
- [ ] Color contrast is readable.
- [ ] Main workflow works on mobile and desktop widths.
- [ ] Palette does not collapse into a single dominant hue.

