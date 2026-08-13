# Feature: Control Panel

## Goal

Provide the left sidebar controls used to manage windows and browser sessions.

## Controls

- Number of windows
- Start Browser
- Pause
- Reset
- Browser mode selector
- Active sessions list
- Default / Layout / Clear presets
- Start Campaign button

## Launch presets

- Default: restore the baseline launch preset for the current workspace
- Layout: mark the launch as a tiled-window arrangement preset
- Clear: clear the selected launch preset back to none

## Notes

- Browser sessions are now backed by live Chrome processes on macOS
- Active sessions reflect the current browser state
- Launch and preset changes are written to the local audit database
