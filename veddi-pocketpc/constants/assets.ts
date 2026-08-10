/**
 * App Asset Exports
 * Standardized references to logos, avatars, and branding icons.
 *
 * `AppLogo` is the in-app brand mark shown on the Devices tab hero and the
 * pairing-screen top bar. We point it at `assets/images/icon.png` (the
 * existing launcher icon declared in `app.json`) so we don't ship a
 * duplicate asset. Resolved via `require` rather than `import` so Metro can
 * inline the image URI at build time — that's the pattern RN uses for
 * `source` props on `<Image>`.
 */
export const AppLogo = require('../assets/images/icon.png');
