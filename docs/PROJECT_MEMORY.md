# Project Memory

## Purpose

Build a Windows GUI email automation tool in Python that ultimately packages into a `.exe`.

## Current direction

- Design first
- Business logic is now being added in parallel
- Gmail integration will use API-based authentication instead of direct password handling
- Persistent audit storage is required for login history, browser sessions, content, settings, and activity logs
- Keep all milestone decisions in markdown files for traceability
- The backend and hosted frontend must always target the dedicated AWS MySQL database
- Before any `.dmg` or `.exe` build, first update the live server frontend and backend, then package the app against the live API and live database

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

- API login for development and hosted deployment
- Username: `admin`
- Password: `admin`
- JWT bearer auth is used by the local API
