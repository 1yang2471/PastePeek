# Changelog

[简体中文](CHANGELOG.md) | English

## v2.0.0-rc.3 (Pre-release, 2026-07-22)

- Added `zh-CN`/`en-US` runtime language switching in the same EXE. Simplified Chinese remains the default, and the choice is stored in `%LOCALAPPDATA%\PastePeek\config.json`.
- Added English copy for the HUD, prediction matrix, preview checklists, active-operation success/refusal feedback, and tray menu. Clipboard text is not translated, and sequence checks, rollback behavior, and the refuse-when-uncertain safety policy are unchanged.
- The HUD `More` menu and tray `Language` menu share one language state, refresh the current result immediately, and restore the choice after restart.
- Long previews now show a scrollbar when they exceed the compact height, so 300px English checklists are not clipped behind a hidden scroll area.

## v2.0.0-rc.2 (Pre-release, 2026-07-20)

- Replaced the application icon with a clipboard, preview eye, and risk marker composition. The transparent ICO now includes 16px through 256px sizes for the tray, window chrome, and Windows Explorer.
- Added release-asset contract tests for ICO sizes, alpha channels, and 16px tray visibility.

## v2.0.0-rc.1 (Pre-release, 2026-07-20)

- Hardened active operations with an "unknown means refuse" policy for signed or ambiguous URLs, code and structured content, standard/registered/unknown non-text formats, embedded HTML/RTF media, missing clipboard sequence numbers, and incomplete rollback state.
- Refreshed the HUD as a quiet light system tool with risk labels, category and action icons, a teal primary action, no-action status text, persistent failure feedback, and 300/400/640px responsive target bars.
- Adjusted preview height to rendered content, kept short previews compact, prevented structured previews from being clipped, and retained a 16px workspace safety margin around the expanded window.
- Completed the release regression and real clipboard, source/EXE GUI, Edge/WPS/WeChat paste-back, and tray UIA acceptance suites.
- Added graceful foreground-window hook fallback, negative-coordinate restoration for secondary screens, taskbar-aware work-area clamping, high-DPI frame safety, Windows file/product version resources, exact release bundle selection, and checkout credential hardening.
- Kept UsageTracker disabled by default and limited the optional local log to about 1 MiB.
- Published the first public minimum pre-release with SHA-256-locked dependencies, GitHub Issue/Pull Request/support/conduct entry points, a dynamic versioned ZIP, full license materials, and a fixed-commit GitHub Actions release workflow.

## 2.0.0 Development Baseline (2026-07-15)

### Features

- Scenario-based paste previews for Chrome, Markdown editors, terminals, code editors, Word, presentations, chat applications, and spreadsheets.
- A horizontal target icon bar with a `More` menu for less common targets.
- Keyboard navigation with `Left`/`Right` target switching and `Enter` to run the primary action.
- Persistent target, layout, startup, and local usage preferences.
- Portable tray lifecycle, single-instance activation, and optional per-user startup.

### Security and Reliability

- Sanitized browser previews using a standard-library HTML parser. Images become local placeholders; scripts, styles, frames, objects, resource declarations, event attributes, and CSS URLs are removed.
- Preserved paragraphs, line breaks, lists, and table boundaries when rich text falls back to plain text.
- Matched rich-text predictions to Windows clipboard format negotiation for terminals, code editors, and Markdown editors.
- Preserved non-text clipboard state across manual and foreground target changes.
- Preserved the last successful snapshot across transient clipboard-open failures and flushed the final local usage session during normal shutdown.
- Added reproducible HUD screenshot rendering, controlled Windows smoke scripts, full GUI/tray UIA acceptance, and locked development dependencies.

### Removed

- Sensitive-information detection and masking.
- Source-type inference. Predictions use only `(content_type, target)`.
- Unused transient configuration fields and ignored vendored dependency fallbacks.

For the Chinese changelog, see [CHANGELOG.md](CHANGELOG.md).
