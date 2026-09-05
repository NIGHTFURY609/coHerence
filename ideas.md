# CoHERence — Visual Direction

## Three possible directions

### Theme Name: Field Notes / Civic Warmth
Very editorial and human: clay, ink, oat, and deep green create the feeling of a beautifully produced civic field guide. The site treats infrastructure data as something that should be legible, felt, and acted on.

**Probability:** 0.07

### Theme Name: Signal / Night Map
A dark, high-contrast cartographic interface with amber signals and electric mint markers. It would feel investigative, precise, and operational—useful for an analyst or city-planning control room.

**Probability:** 0.03

### Theme Name: Soft Systems / New Commons
A light, optimistic system of overlapping forms, generous white space, and coral-led moments of emphasis. The visual language is supportive without being sentimental, framing public infrastructure as a shared act of care.

**Probability:** 0.08

## Selected direction: Field Notes / Civic Warmth

### Design Movement
Contemporary editorialism blended with civic design and data journalism: tactile paper-like surfaces, confident serif display type, crisp sans-serif UI text, and map-inspired marks that turn research into a human-scale story.

### Core Principles
1. **Evidence should feel approachable.** Data visualizations use generous spacing, clear labels, and warm contrast rather than cold dashboard density.
2. **Care is infrastructure.** Copy and motion acknowledge lived experience without using fear as a visual shortcut.
3. **Asymmetry creates agency.** Sections move through staggered columns, offset cards, and a recurring vertical field line instead of repetitive centered blocks.
4. **Every interaction explains something.** Hover, scroll, and tap states reveal context, change scale, or help users compare—not just add sparkle.

### Color Philosophy
The palette pairs **deep ink (#173B36)** for trust and groundedness, **oat (#F7F1E7)** for calm, **clay (#D85C45)** for action, and **pistachio (#C9D9B2)** for possibility. The colors are earthy and specific, avoiding stereotypical pink while keeping enough warmth to feel welcoming. Coral is reserved for the moments where the system asks for attention; green holds structural content; oat gives the experience room to breathe.

### Layout Paradigm
An editorial scrolling field guide: a sticky left rail on desktop becomes a compact progress pill on mobile; content drifts from a warm hero into a split-screen map story, then a pinned metric rail, then an actionable closing section. Cards are offset and partially overlapping, with a persistent vertical rule echoing a map coordinate axis.

### Signature Elements
- A **coordinate rail** that shows the current chapter and uses a moving clay marker as the page progresses.
- **Contour-line / route motifs** drawn as thin SVG paths and layered behind key numbers.
- **Facility tags** styled like small punched field labels: safety, care, health, transit.

### Interaction Philosophy
Interactions should feel like unfolding a map or annotating a field note. A hover reveals the consequence of a data point; a tap opens the explanation inline. Buttons have tactile press feedback and slightly magnetic hover movement on desktop, but become plain, touch-friendly controls on mobile.

### Animation
- On load, the wordmark and hero statement rise in with a small vertical offset, while the contour field drifts slowly into place.
- ScrollTrigger reveals copy in editorial chunks and draws the chapter marker down the coordinate rail.
- The facility map uses a masked image reveal and slow parallax so the map feels discovered, not dropped in.
- Numbers count only when their section enters the viewport, with reduced-motion fallback to the final value.
- Cards use spring-like transform transitions; no animation should alter layout dimensions.
- `prefers-reduced-motion` disables parallax, cursor-following, and count interpolation while preserving opacity/visibility and all content.

### Typography System
- **Display:** Fraunces, 600/700, with italic for emotional emphasis. Large statements should feel authored, not corporate.
- **Body/UI:** Manrope, 450/600/700, for clear data labels, navigation, and utility copy.
- Hierarchy: display headlines use tight leading and slightly negative tracking; metadata uses uppercase 11px labels with 0.14em tracking; paragraphs stay between 16–19px with comfortable line-height.

### Brand Essence
**CoHERence makes the invisible infrastructure gap visible, so cities can design around women’s real lives—not assumptions.**

Personality: **grounded, incisive, generous**.

### Brand Voice
Headlines are direct, human, and quietly challenging. CTAs are invitations to inspect or act, never hype. Microcopy names what the interface is doing and why it matters.

Example lines:
- “The missing facility is a data point before it becomes a daily burden.”
- “See where care should meet the commute.”

### Wordmark & Logo
The wordmark is set as `CoHERence` with a deliberate capital H/E/R intervention, paired with a simple symbol: two offset contour paths converging into a small open circle. The mark suggests a route becoming legible and a system becoming coherent. The symbol should work alone as the favicon and as the navigation mark.

### Signature Brand Color
**CoHERence Clay — #D85C45.** A grounded terracotta that signals action, warmth, and human urgency without turning the brand into a stereotypical “women’s” palette.

## Implementation reminders

- All page/component files should begin with a short comment tying the file to Field Notes / Civic Warmth.
- Keep motion purposeful, transform/opacity based, and gated by reduced-motion preferences.
- Use semantic landmarks, visible focus rings, keyboard-accessible controls, and touch-friendly targets.
- Prefer inline SVG for diagrammatic motifs and CSS texture over heavy imagery when that keeps the experience faster.
