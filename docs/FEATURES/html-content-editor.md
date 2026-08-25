# Feature: HTML Content Editor

## Goal

Provide a dedicated workspace for editable campaign attachment content.

## Layout

- Per-tab HTML Code and Text Editor modes
- Rich-text controls for fonts, size, color, bold, italic, underline, and left/center/right alignment
- Bulleted and numbered lists, undo/redo, and clear formatting
- Rich-text font family, size, bold, italic, underline, and color controls
- Embedded image upload and variable insertion
- Separate rendered preview window
- Per-tab mode and content persistence
- PDF, image, Word, Excel, and PowerPoint conversion through the shared attachment pipeline
- Attachment format and file-name configuration

## Notes

- HTML Code mode preserves and sends the entered HTML source.
- Text Editor mode serializes the formatted document to HTML before variable replacement and conversion.
- Images inserted through Text Editor are embedded as data URLs so generated attachments do not depend on local file paths.
