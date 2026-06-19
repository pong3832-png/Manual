# camp-platform Frontend Design

## 1. Design Direction

camp-platform is a campaign discovery marketplace for Korean creators. The interface should feel like a fast browsing surface for opportunities, not an admin dashboard. Use the structural clarity of Airbnb, the reading calm of Notion, and the existing warm editorial tone already present in the product.

The experience should communicate:
- Browse first, decide fast
- Opportunity density without visual noise
- Warm, trustworthy marketplace energy
- Strong card scanning on desktop and mobile

This is not a fintech UI, terminal UI, or generic SaaS dashboard. Avoid cold enterprise styling, hard black surfaces, and neon accents.

## 2. Visual Theme & Atmosphere

- Base mood: warm editorial marketplace
- Canvas: soft parchment instead of pure gray
- Surfaces: ivory cards over a slightly warmer page background
- Accent: terracotta for primary actions and active filters
- Typography tone: confident, compact, readable Korean UI
- Density: medium-high information density with generous grouping and whitespace between sections

The page should feel like a curated campaign board. Users should be able to skim cards, filters, and urgency signals in seconds.

## 3. Color Palette

### Core Neutrals
- `--bg-page: #f5f4ed`
- `--bg-surface: #faf9f5`
- `--bg-surface-muted: #f2f0e8`
- `--text-primary: #141413`
- `--text-secondary: #4d4c48`
- `--text-muted: #87867f`
- `--border-subtle: #e8e6dc`
- `--border-strong: #d4d1c6`

### Brand Accent
- `--accent-primary: #c96442`
- `--accent-primary-hover: #a8512f`
- `--accent-soft: #f7ede7`

Use terracotta as the singular product accent for:
- Primary CTA
- Active filter chips
- Selected navigation state
- Key emphasis badges

Do not flood large surfaces with the accent color.

### Semantic Signals
- Urgent / closing soon: `#dc2626`
- Positive / low competition: `#059669`
- Informational / counts: `#2563eb`

### Category Backgrounds

These are lightweight card hero backgrounds, not full-page themes:
- Food: `#FFF3F0`
- Cafe: `#FFF8E8`
- Beauty: `#F8F1FF`
- Stay: `#F0F4FF`
- Living: `#F2F8FF`
- Fashion: `#FFF0F5`
- Experience: `#F0FFF8`
- Other: `#F4F4F5`

## 4. Typography

### Font Family
- Primary: `"Noto Sans KR", "Apple SD Gothic Neo", -apple-system, sans-serif`
- English fallback: system UI stack is acceptable

### Hierarchy

| Role | Size | Weight | Line Height | Letter Spacing | Notes |
|------|------|--------|-------------|----------------|-------|
| Hero Title | 32-40px | 900 | 1.08-1.12 | -0.04em | Primary page titles |
| Section Title | 24-28px | 800 | 1.15 | -0.02em | Major section headers |
| Card Title | 18-22px | 800 | 1.25 | -0.02em | Campaign card headline |
| Body | 14-15px | 400-500 | 1.6 | normal | Standard reading text |
| UI Label | 13-14px | 600-700 | 1.4 | normal | Buttons, tabs, controls |
| Meta / Badge | 10-12px | 700-800 | 1.3 | 0.08em | Eyebrows, pills, counters |

### Type Principles
- Headlines should be compact and bold.
- Body copy should stay short and readable.
- Uppercase micro-labels are acceptable only for section eyebrows and stat labels.
- Avoid oversized paragraph text or thin display weights.

## 5. Layout Principles

### Shell
- Desktop uses a left sidebar plus flexible main stage.
- Content max width should stay around 1040-1100px in the main reading area.
- Major sections should be stacked with 24-32px vertical rhythm.

### Grid
- Campaign cards: responsive auto-fill grid, minimum 260px columns on desktop
- Summary stats: 4-up desktop, 2-up tablet, 1-up small mobile
- Hero sections: two-column on desktop, stacked on smaller screens

### Whitespace
- Tight inside cards, generous between cards and sections
- Filters should feel compact and operational
- Hero areas should breathe more than results areas

## 6. Components

### Sidebar / Navigation
- Surface: ivory card-like rail with subtle border
- Active nav: terracotta soft background + terracotta text
- Inactive nav: muted warm gray
- Count badges should be compact and high-contrast

### Hero Sections
- White/ivory surface with clear border and soft shadow
- Left side: eyebrow, bold title, short description, compact action cluster
- Right side: live stats or platform overview panel
- No oversized abstract gradients

### Search
- Large single-row search box
- Surface: ivory
- Focus state: terracotta border + subtle outer ring
- Placeholder text should remain muted, not low-contrast gray-on-gray

### Filters
- Use pills/chips
- Default: ivory with subtle border
- Active: terracotta fill with white text
- Sorting chips may use dark fill for contrast, but keep it warm near-black, not true black

### Campaign Cards
- Card shell: ivory surface, rounded corners, soft lift
- Top hero: category-tinted color field with platform/category pills
- Title is the primary element
- Meta row should prioritize location and D-day
- Provision/reward box should be visually distinct but quiet
- Footer must clearly separate urgency, competition, and action

### Status / Profile Cards
- Same surface language as campaign cards
- Use stat blocks, badges, and grouped actions
- No heavy panel chrome or dashboard-style complexity

### Modals / Sheets
- Light sheet over dim backdrop
- Rounded top corners on mobile sheet
- Information grouped into small bordered boxes
- Primary CTA must dominate the bottom action area

## 7. Radius & Elevation

### Radius Scale
- Small: `10px`
- Medium: `16px`
- Large: `22px`
- XL: `28px`
- Pill: `999px`

### Shadow System
- Card: `0 2px 8px rgba(20,20,19,0.06), 0 0 0 1px #e8e6dc`
- Float: `0 8px 24px rgba(20,20,19,0.10), 0 0 0 1px #e8e6dc`

Shadows should feel soft and warm. Avoid hard blue-gray shadows or dramatic floating glass effects.

## 8. Responsive Behavior

- Under 1000px: hero panels and map layout stack vertically
- Under 768px: sidebar hides, mobile header and bottom navigation appear
- Under 480px: single-column card and stat layouts

Mobile priorities:
- Fast scanning
- Thumb-friendly navigation
- Full-width CTAs where helpful
- No cramped horizontal overflow except intentional chip rows

## 9. Do

- Keep the UI warm, crisp, and readable
- Use terracotta sparingly but consistently
- Make cards the primary browsing object
- Emphasize urgency and competition with compact badges
- Preserve category-tinted hero areas for fast visual scanning
- Maintain one shared visual language across Home, Explore, Map, Status, and Profile

## 10. Don't

- Don't introduce dark-mode-first Linear or Supabase styling into the default theme
- Don't use purple as a dominant product accent
- Don't make the interface look like a metrics dashboard
- Don't flatten everything into borderless white blocks
- Don't overuse gradients, blur, glassmorphism, or neon
- Don't let platform colors overpower the core brand system

## 11. Reference Mapping From awesome-design-md

Primary reference:
- Airbnb: listing marketplace structure, browse-first hierarchy, card-forward scanning

Secondary reference:
- Notion: warm neutral restraint, whisper borders, readable section rhythm

Explicitly not chosen as primary reference:
- Linear: too dark and too technical for this marketplace
- Supabase: too developer-platform oriented
- Clay: useful for warmth, but too playful for default product chrome

## 12. Agent Prompt Guide

When generating or refactoring UI for this project, use this prompt framing:

"Design this as a warm campaign discovery marketplace for Korean creators. Use a parchment page background, ivory cards, terracotta as the only strong accent, bold compact headings, and browse-first campaign cards inspired by Airbnb's marketplace clarity and Notion's restrained warm neutrals. Keep the UI light, tactile, and highly scannable on both desktop and mobile."
