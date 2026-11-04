---
target: frontend dashboard (App.tsx + components)
total_score: 32
max_score: 40
na_heuristics: 
p0_count: 0
p1_count: 3
target_identity: "file:/Users/meya/Desktop/sih/frontend/src/App.tsx"
target_fingerprint: "sha256:886b1eb80b3ed1ba5a4b0bbee427150a3476261d502c481d203f03599e359cd9"
target_path: /Users/meya/Desktop/sih/frontend/src/App.tsx
timestamp: 2026-09-03T13-20-09Z
slug: frontend-src-app-tsx
closed: true
---
## Design Health Score

| # | Heuristic | Score | Key Issue |
|---|---|---|---|
| 1 | Visibility of System Status | 2 | Vehicles/Cameras fetch once on mount, never poll — only Alerts (20s) and the WS feed update. |
| 2 | Match System / Real World | 4 | Terminology, tiering, Bengaluru geography all product-accurate. |
| 3 | User Control and Freedom | 3 | Collapse toggle clips off-screen at narrow widths. |
| 4 | Consistency and Standards | 3 | AlertsPanel rows are real buttons; VehicleTable/CameraTable rows are bare tr onClick. |
| 5 | Error Prevention | 4 | Divide-by-zero guard, stale-trajectory guard. |
| 6 | Recognition Rather Than Recall | 4 | Persistent legend, filter counts, selection retained across tabs. |
| 7 | Flexibility and Efficiency | 3 | No keyboard shortcuts; filter panel forgets open/closed state. |
| 8 | Aesthetic and Minimalist Design | 3 | Glow/shimmer/pulse density plus 9-11px type risks demo-over-scan. |
| 9 | Error Recovery | 4 | Real WebGL/basemap failure copy, ErrorState + retry everywhere. |
| 10 | Help and Documentation | 2 | No onboarding, no tier glossary, no shortcut reference. |
| **Total** | | **32/40** | **Good** |

## Design Specificity Verdict

LLM: confidence-tier visual language is genuinely product-grounded (solid cyan CONFIRMED / dashed amber INFERRED / dotted rose UNCERTAIN across map, drawer, chart); honest "not yet available" Analytics cards; slips toward generic ops-demo in the amount of ambient glow/shimmer/pulse chrome vs Operate-mode restraint.

Detector: 1 static finding (side-tab, AlertsPanel.tsx:93). Browser pass: 42-106 findings/view, dominated by undersized-ui-text, text-occlusion (worst in trajectory drawer), dark-glow, plus ai-color-palette, gpt-thin-border-wide-shadow, nested-cards/edge-flush-cards. ai-color-palette flagged as the one rule to weigh with more skepticism (statistical match, not aware the palette was a deliberate discussed choice).

## Priority Issues

[P1] Vehicles/Cameras tables never refresh, contradicting "real-time is a hard requirement." Fix: poll or wire to WS; show "as of HH:MM:SS" per table. -> /impeccable harden

[P1] Primary vehicle/camera selection is mouse-only (bare tr onClick, no keyboard path), while AlertsPanel does the identical interaction correctly as a button. Fix: convert to button or add role/tabIndex/keyboard handling + focus-visible ring. -> /impeccable audit

[P1] Collapse toggle clips off-screen at narrow widths (verified via boundingBox: x:-12/x:378 at 390px viewport). Fix: anchor to viewport edge, not the collapsed panel's own box. -> /impeccable adapt

[P2] Text legibility crisis, worst in trajectory drawer: fg-faint ~3.7:1 contrast on live data (timestamps, endpoint labels) + undersized-ui-text/tiny-text (up to 32 hits) + text-occlusion (up to 40 hits) concentrated in the drawer. Fix: lighten fg-faint past 4.5:1 or restrict to decoration; audit drawer occlusion. -> /impeccable typeset

[P3] Ambient glow/border chrome reads closer to generic "AI dashboard" than restrained Operate-mode tool (dark-glow, gpt-thin-border-wide-shadow, side-tab, nested-cards/edge-flush-cards all agree with LLM's "cinematic demo" read). Fix: conditional/thinner side-tab border, fewer simultaneous glow sources, flatten unneeded nested-card borders. -> /impeccable quieter

## Persona Red Flags

Alex (Power User): stale tables burn trust; zero keyboard shortcuts; FilterBar forgets open state each session; sort always resets to ascending.

Sam (Accessibility-Dependent): cannot select vehicle/camera by keyboard at all; map canvas has no aria-label; fg-faint contrast gap hits nearly every timestamp/caption; no focus-visible beyond a couple inputs. Credit: prefers-reduced-motion correctly honored globally.

## Minor Observations

- Tabs.tsx hardcodes any nonzero alert badge to severity-high red regardless of actual severity mix.
- CollapsiblePanel.tsx animates width/margin directly (non-GPU-accelerated).
- TopBar.tsx live clock has no "IST" label.
- ComingSoonCard.tsx dashed border reads as broken/placeholder before copy is read.
- MapLegend.tsx fixed non-collapsible ~200px eats over half the 390px mobile viewport.

## Questions to Consider

1. Was cutting Vehicles/Cameras polling a deliberate scope call, or did "real-time" quietly narrow to just the live-feed sidebar?
2. Does the glow/shimmer/pulse stack earn its cognitive cost for a daily operator, or do judges vs operators need two visual intensities?
3. The confidence-tier system is the differentiator but only reachable via mouse — is "explainable tracking" actually accessible, or only visually explainable?
