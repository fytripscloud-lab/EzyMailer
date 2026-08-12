# Update Log

## 2026-08-12

- Created the first project memory and update records
- Added the Python GUI scaffold for login and the dashboard shell
- Added the left sidebar control panel, top bar, browser mode selector, and active sessions list
- Added the tabbed workspace placeholders for customer database, subjects + body, content, settings, sender, and tags
- Added local design-only login credentials for the initial milestone
- Added Windows packaging files for future `.exe` generation with PyInstaller
- Reworked the authenticated shell into a modern dark UI with sidebar logging and richer tab placeholders
- Expanded the dashboard into a complete design pass covering Data, Subject+Body, Content, Settings, Blaster, and Tags
- Aligned the top bar branding to the enterprise-style reference layout
- Added compact custom window chrome, toast notifications, and modal output options
- Reworked alerts into centered in-app toasts with compact dark styling and a custom confirmation modal
- Added custom minimize and maximize controls
- Shifted the app chrome toward a VS Code-style dark editor theme with flatter panels and muted borders
- Removed the per-session open action and made the close control remove browser windows from the active session list
- Redesigned the login page into a centered single-card sign-in shell
- Added a modal robot-style launch loader for browser window startup
- Added fade-out animation when closing an active session row
- Renamed the launch preset button from `Tile` to `Layout`
- Added hover tooltips across the main controls and tab actions
- Added a dedicated HTML preview window for the subject/body and content editors
- Added preview toolbar controls for reload, zoom, and raw HTML source viewing
