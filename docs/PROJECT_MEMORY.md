# Project Memory

## Purpose

Build a Windows GUI email automation tool in Python that ultimately packages into a `.exe`.

## Current direction

- Design first
- Business logic later
- Gmail integration will use API-based authentication instead of direct password handling
- Keep all milestone decisions in markdown files for traceability

## UI goals

- Login page
- Main dashboard after login
- Left logo area and left control sidebar
- Top navigation bar
- Tabbed workspace
- Modern dark enterprise-style layout inspired by the provided screenshots
- Top bar branding aligned to the 3S Ultimate Enterprise style
- Compact dark chrome with a frameless custom window and custom close control

## Core panels

- Control panel
- Browser mode selector
- Active sessions list
- Data
- Subjects + Body
- Content
- Settings
- Blaster
- Tags

## Design scope

- Pending emails input and validation view
- Subject and body editor with spintax-aware design
- HTML content editor with attachment section
- Sending settings and proxy/startup controls
- Email blasting progress and send log
- Dynamic tags grid and manual custom tags
- Activity log in the sidebar
- Toast notifications for browser mode and launch feedback
- HTML message code view and an output options modal

## Authentication placeholder

- Temporary local login for design work
- Username: `admin`
- Password: `admin`
- Replace with API/OAuth flow in a later milestone
