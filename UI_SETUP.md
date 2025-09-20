## UI setup and structure

This document explains the browser UI code structure, responsibilities of each module, how the app boots, what localStorage keys are used, and how the UI communicates with the Python backend.

### 1) Directory layout (frontend)

```
static/
  index.html                # Main UI page
  css/
    styles.css             # Global theme + layout
    patient.css            # Patient registration page
  js/
    app.js                 # Legacy monolith boot (kept for compatibility)
    core.js                # (optional) Core app bootstrap if using modules
    boot.js                # (optional) Bootstrapping helpers for modules
    ui/                    # UI-layer modules (DOM + events)
      sidebar.js           # Sidebar open/close, overlay, sessions list
      modals.js            # User/doctor modal, settings modal, edit-title modal
      patient.js           # Patient section: typeahead, status, select
      theme.js             # Theme/font-size handling
      voice.js             # Web Speech API setup (optional)
      utils.js             # Small DOM utilities (qs, on, etc.)
    chat/                  # Chat logic modules
      messages.js          # Render and manage messages in chat pane
      sessions.js          # Client-side session CRUD (local + fetch from backend)
      api.js               # Fetch helpers to talk to backend endpoints
      state.js             # Ephemeral UI state (current user/patient/session)

patient.html                # Patient registration page
```

Notes:
- If `core.js` and `boot.js` are present and loaded as type="module", they should import from `js/ui/*` and `js/chat/*`. If you continue using `app.js`, it should delegate to these modules (or keep the current inline logic).

### 2) Boot sequence

Minimal boot (non-module):
- `index.html` loads `app.js` (non-module). `app.js` wires events, restores local state, applies theme, renders sidebar sessions, and binds modals.

Module-based boot (recommended):
- `index.html` includes:
  - `<script type="module" src="/static/js/core.js"></script>`
  - `core.js` imports from `ui/*` and `chat/*`, builds the app, and calls `boot.init()`.
  - `boot.js` provides `init()` that wires all UI modules in a deterministic order.

Expected init order:
1. Load preferences (theme, font size) and apply to `document.documentElement`.
2. Restore user (doctor) profile from localStorage.
3. Restore selected patient id from localStorage and, if present, preload sessions from backend.
4. Wire global UI events: sidebar toggle, outside-click overlay, send, clear, export.
5. Wire modals: user/doctor modal, settings modal, edit-session-title modal.
6. Wire patient section: typeahead search + selection + status.
7. Render current session messages.

### 3) State model (in-memory)

- `state.user`: current doctor `{ id, name, role, specialty, createdAt }`.
- `state.patientId`: 8-digit patient id string kept in localStorage under `medicalChatbotPatientId`.
- `state.currentSession`: `{ id, title, messages[], createdAt, lastActivity, source }`.
- `state.sessions`: local session cache (for non-backend sessions).

LocalStorage keys:
- `medicalChatbotUser`: current doctor object.
- `medicalChatbotDoctors`: array of `{ name }` (unique, used for the dropdown).
- `medicalChatbotPatientId`: selected patient id.
- `medicalChatbotPreferences`: `{ theme, fontSize, autoSave, notifications }`.

### 4) Components and responsibilities

UI modules (ui/*):
- `sidebar.js`: opens/closes sidebar, manages `#sidebarOverlay`, renders session cards, handles outside-click close.
- `modals.js`: shows/hides user/doctor modal, settings modal, edit-title modal. Populates doctor dropdown with a first item "Create doctor user..." and injects current doctor name if missing.
- `patient.js`: typeahead over `/patients/search?q=...`, renders suggestions, sets `state.patientId` and persists to localStorage, triggers sessions preload.
- `theme.js`: reads/writes `medicalChatbotPreferences`, applies `data-theme` on `<html>`, sets root font-size.
- `voice.js`: optional Web Speech API wiring to fill `#chatInput`.

Chat modules (chat/*):
- `messages.js`: adds user/assistant messages, formats content, timestamps, scrolls to bottom.
- `sessions.js`: saves/loads local sessions, hydrates backend sessions (`GET /sessions/{id}/messages`), deletes/renames sessions.
- `api.js`: wrappers around backend endpoints (`/chat`, `/patients/*`, `/sessions/*`). Adds `Accept: application/json` and logs responses.
- `state.js`: exports a singleton state object used by UI and chat modules.

### 5) Backend endpoints used by the UI

- `POST /chat` — main inference call.
- `GET /patients/search?q=...&limit=...` — typeahead. Returns `{ results: [{ name, patient_id, ...}, ...] }`.
- `GET /patients/{patient_id}` — patient profile (used by patient modal).
- `POST /patients` — create patient (used by patient.html). Returns `{ patient_id, name, ... }`.
- `PATCH /patients/{patient_id}` — update patient fields.
- `GET /patients/{patient_id}/sessions` — list sessions.
- `GET /sessions/{session_id}/messages?limit=...` — hydrate messages.

### 6) Theming

- CSS variables are declared under `:root` and overridden under `[data-theme="dark"]`.
- On boot, the app reads `medicalChatbotPreferences.theme` and applies:
  - `auto` => matches `prefers-color-scheme`.
  - `light`/`dark` => sets `document.documentElement.dataset.theme` accordingly.

### 7) Patient typeahead contract

- Input: `#patientIdInput`.
- Suggestions container: `#patientSuggestions` (absolute, below input).
- Debounce: ~200 ms. Request: `GET /patients/search?q=<term>&limit=8`.
- On selection: set `state.patientId`, persist to localStorage, update `#patientStatus`, call sessions preload, close suggestions.
- On Enter:
  - If exact 8 digits, call `loadPatient()`.
  - Otherwise, search and pick the first match if any.

### 8) Sidebar behavior

- Open: click `#sidebarToggle`.
- Close: clicking outside (main area) or on `#sidebarOverlay` hides the sidebar on all viewports.

### 9) Doctor dropdown rules

- First option is always "Create doctor user..." (value: `__create__`).
- If the current doctor name is not in `medicalChatbotDoctors`, it is inserted and saved.
- Choosing the create option reveals an inline mini-form to add a new doctor; Confirm inserts and selects it.

### 10) Voice input (optional)

- If using `voice.js`: checks `window.SpeechRecognition || window.webkitSpeechRecognition`.
- Streams interim results into `#chatInput`, toggled by `#microphoneBtn`.

### 11) Patient registration flow

- `patient.html` posts to `POST /patients` with name/age/sex/etc.
- On success, shows a modal with the new Patient ID and two actions: Return to main page, Edit patient profile.
- Stores `medicalChatbotPatientId` and redirects when appropriate.

### 12) Troubleshooting

- Sidebar won’t close: ensure `#sidebarOverlay` exists and that `sidebar.js`/`app.js` wires outside-click and overlay click listeners.
- Doctor dropdown empty: confirm `medicalChatbotDoctors` exists or `populateDoctorSelect()` runs on opening the modal.
- Typeahead doesn’t show results: open network tab and hit `/patients/search?q=test`; ensure 200 and JSON. Logs are printed by FastAPI (see server console).
- Theme not changing: ensure `theme.js` sets `data-theme` on `<html>` and `styles.css` uses `[data-theme="dark"]` overrides.

### 13) Migration from app.js to modules

If you refactored into `ui/*` and `chat/*`:
1. Ensure `index.html` loads `core.js` as a module.
2. In `core.js`, import and initialize modules in the order described in Boot sequence.
3. Keep `app.js` only if you need compatibility; progressively move code into the relevant module files.


