SIGN IN TO CONTINUE
- Username: User enters the admin username.
- Password: User enters the password.
- Sign in: System sends login request to backend, verifies credentials, checks device restriction and validity, then opens dashboard if valid.
BROWSER SESSION CONTROL
- Start browser: Creates and launches the required browser windows/sessions.
- Pause: Temporarily stops campaign actions without closing sessions.
- Reset: Clears current browser state and starts fresh sessions.
- Default: Loads the default browser/session configuration.
- Layout: Applies the selected multi-window layout.
- Clear: Removes current session settings or active session list.
BROWSER MODE
- Incognito: Opens browser in private mode with no persistent profile.
- Normal: Opens browser with regular profile behavior and saved session support.
ACTIVE SESSION
- Shows all browser windows currently created by the app.
- Each row should track window state like running, paused, closed, or failed.
- Used to monitor which browser instance is being used for sending.
ACTIVITY LOG
- Stores every important action performed in the app.
- Example: login, browser start, email loaded, attachment selected, campaign started, send result.
- Used for debugging, audit trail, and user tracking.
START CAMPAIGN BUTTON
- Starts the campaign only after required data is ready.
- Checks recipients, subject/body, attachment, browser sessions, and settings.
- If something is missing, it should stop and show an error.
- If valid, it begins sending email step by step.
DATA
- Customer emails: Stores recipient email addresses entered by user.
- Domain filter: Filters valid emails based on Gmail-only or all allowed domains.
- Load from file: Reads email list from uploaded file and populates the data.
- Clear List: Removes all loaded recipient emails.
- Validate and count: Checks valid, invalid, and duplicate emails, then shows totals.
SUBJECT + BODY
- Subject: Stores the main email subject text.
- New subject: Creates or edits subject content.
- Import CSV: Loads subject and body values from a CSV file.
- Logic: The app should allow tag replacement inside subject before sending.
BODY TABS
- Bodies: Lets user manage multiple email body versions.
- Tab label: Gives each body template a name.
- Mode: Chooses how the body content is handled, such as text, HTML, or template mode.
- Upload: Imports body content from a file.
- Reset body: Clears the current body editor content.
- Logic: The body should support variable replacement before send time.
ATTACHMENT
- + button: Adds a new attachment content block or template tab.
- Upload: Loads HTML or attachment source from file.
- Reset content: Clears the current attachment content.
- Tab label: Names the attachment template.
- Text area: Allows pasting or editing raw HTML content.
- Logic: HTML can be converted into attachment output before sending.
ATTACHMENT FORMAT
- Convert: Converts the source content into selected output file format.
- File format: Chooses output type like PDF, DOCX, XLSX, PPTX, or HTML-based output.
- File Name: Sets the final attachment file name.
- Logic: system should generate file using user-selected format and name, then attach it to the email.
SENDING SETTINGS
- Per-sender limit: Sets maximum emails allowed per sender or window.
- Delay between: Sets wait time between consecutive sends.
- Delay type: Chooses whether delay is in seconds, minutes, or custom behavior.
- Retry failed sends: Automatically retries failed delivery attempts.
- Email sender order: Chooses the order recipients are processed.
- Window send mode: Decides whether send happens from one window or multiple windows.
- Logic: these settings control speed, load distribution, and failure handling.
AI ASSISTANT
- Provider: Selects the AI service.
- API Key: Authenticates with the provider.
- Model: Chooses the model to use.
- Status: Shows whether AI is connected and ready.
- Logic: AI can be used for content generation, subject creation, or template support.
TAGS
- Dynamic tags: Auto-generated placeholders pulled from recipient or campaign data.
- Manual custom tags: User-defined key/value placeholders.
- Logic: tags are replaced in subject, body, attachment content, and file name before sending.
CUSTOMER VARIABLES
- email: Identifies the recipient record.
- Variable: Placeholder name like name, company, city.
- Value: Actual replacement text for that variable.
- Save/update: Stores or updates the variable mapping.
- Delete selected: Removes selected variable mappings.
- Refresh: Reloads variable data from storage.
- Clear: Resets current input fields.
- List: Shows all saved variable records.
- Logic: these variables must be available during template rendering.
CAMPAIGN
- Active windows: Shows which browser windows are available for send automation.
- Campaign Progress: Displays how much of the campaign is completed.
- Refresh: Reloads live campaign state from backend.
- Start campaign button: Starts sending process across active browser windows.
- Send log: Shows detailed send results, failures, retries, and progress.
- Logic: the campaign module coordinates recipient selection, browser actions, content merge, attachment generation, and send execution.