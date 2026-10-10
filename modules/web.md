# Module: Web

**Load when:** building or changing websites, UI components, CSS/JS, frontend pages.
**Skip loading for:** T0 tweaks (a color value, a typo in text) — just edit and diff.

## Evidence ladder (cheapest sufficient first)
1. **T0/T1 text or config change:** the diff itself. Read it; confirm only intended lines changed.
2. **T1 small style change:** source check + targeted screenshot if a browser/vision is available.
   If not: state "visual result UNVERIFIED" and give the user a one-line command to check.
3. **T2 component/section:** render the page; screenshot the viewport you changed; look at it;
   check console errors (`page.on('console')` / DevTools). One responsive width where layout risk
   exists (e.g., 375px for anything with wrapping text).
4. **T3 full site/page:** screenshots at desktop (~1440), tablet (~768), mobile (~375); console
   clean; interaction states (hover/focus/open) if interactive; empty/error states if applicable;
   basic accessibility pass (contrast on real text, alt on meaningful images, keyboard path to
   primary actions, semantic landmarks).

## Tools
Host browser/vision first. Otherwise Playwright or Puppeteer if installed:
`npx playwright screenshot --viewport-size=375,812 <url> shot.png`. If neither exists, degrade
honestly — never claim visual quality from code alone.

## Common failure modes
- Text overflow/clipping at narrow widths; horizontal scroll from fixed widths.
- Unstyled default focus states; contrast failures on decorative palettes.
- Layout shift from late-loading fonts/images.
- Claiming "responsive" because a media query exists, without looking at 375px.
- Generic statistical defaults (centered hero + three cards + fade-up everything) shipped without
  checking them against the brief. That's only a defect if it fails the intent — judge, don't ban.

## Cannot verify here
Motion *feel* requires watching it (recording or host vision); CSS keyframes are not proof of
smoothness. Real-user font rendering, third-party embed behavior, and production performance need
live environments; say so when untested.

## Stopping conditions
One critique pass at T2. Re-screenshot only after meaningful changes. Ship with named gaps rather
than polishing trivia.

**Good verification:** "Inspected `shots/home-375.png`: nav collapses correctly, headline wraps to
2 lines, no horizontal scroll; console log captured in `shots/console.txt`, zero errors."
**Bad verification:** "Added media queries, so it should be responsive."
