# Changelog

## v4.4 (2026-06-18)

- **Fixed:** code duplication in repair logic (`_repair` simplified to try PyPI first, git fallback once)
- **Fixed:** password prompt no longer freezes the GUI (moved to background thread with `threading.Event`)
- **Added:** confirmation dialogs before Flash and Wipe operations
- **Added:** type hints to all function signatures
- **Added:** visible Exit button in sidebar
- **Fixed:** USB detection no longer lazily imports `pyusb` every 1.5s
- **Fixed:** `ActionCard` widget no longer binds events twice
