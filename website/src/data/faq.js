export const faqs = [
  {
    q: 'What is EzyMailer?',
    a: 'EzyMailer is a desktop app for Windows and macOS that helps you compose, personalise and send email campaigns through Gmail windows, the Gmail API or any SMTP server. It combines a recipient manager, a multi-body editor, an attachment designer, dynamic tags, AI writing and a live campaign dashboard in one place.',
  },
  {
    q: 'Which platforms are supported?',
    a: 'Windows 10/11 (64-bit) and macOS 12 Monterey or later on both Apple silicon and Intel Macs. Both apps ship with their own browser runtime, so you do not need to install Chrome separately.',
  },
  {
    q: 'Do I need an account to use the app?',
    a: 'Yes. EzyMailer requires an active account to sign in. Accounts are licensed per device and have a validity period managed by your administrator.',
  },
  {
    q: 'Which sending modes are there?',
    a: 'Three. Manual drives real Gmail windows, much like you would by hand. API JSON sends through Google’s official Gmail API — EzyMailer can create the Google Cloud project and OAuth client for you, one per Gmail account. SMTP sends through any mail server (Gmail App Passwords, Google Workspace or your own host) with no browser at all. The mode is locked while a campaign is running.',
  },
  {
    q: 'Can I send a test email before the real campaign?',
    a: 'Yes. Every sender in Active Sessions has a Try button: enter your own address and EzyMailer sends one email from that sender using your real subject, body, attachment and sender name, with tags filled in.',
  },
  {
    q: 'Can I start or stop just one sender?',
    a: 'Yes. Each Gmail window, API account and SMTP credential has its own Start and Stop. Start one on its own or add more while a campaign runs; Stop pauses only that sender and the others take over the remaining emails. No recipient is ever sent twice.',
  },
  {
    q: 'How do I upload SMTP credentials?',
    a: 'Click Sample next to SMTP Credentials to download the format, then upload one or more CSV or Excel (.xlsx / .xls) files with an email and password per row. Gmail accounts need an App Password. Server, port and security are set with the ⚙ button.',
  },
  {
    q: 'What does the Per sender limit do?',
    a: 'It caps how many emails each sender — a Gmail window, API account or SMTP credential — sends in one campaign. It is one value shared by every mode and by Settings. If your list is larger than senders × limit, EzyMailer warns you and keeps the rest in the customer list for later.',
  },
  {
    q: 'What name do recipients see as the sender?',
    a: 'For SMTP and Gmail API you choose: Auto (one random name per sender, kept for every campaign), Auto (Random Name), $fullname, $spanishname, Custom, or — for Gmail API — the Google account’s own name. Gmail windows always send with the account’s own name.',
  },
  {
    q: 'Where are my Gmail logins and recipient lists stored?',
    a: 'On your computer. Gmail sessions, Gmail API credentials, SMTP credentials, recipient lists and campaign content are kept locally by the app. Account sign-in, licence checks, activity records and daily sent-email totals are handled by the EzyMailer service. See the Privacy Policy for details.',
  },
  {
    q: 'Which AI providers can I use?',
    a: 'OpenAI, Anthropic and DeepSeek. You supply your own API key and pick the model. AI is entirely optional.',
  },
  {
    q: 'What attachment formats can EzyMailer generate?',
    a: 'PDF, Word (DOCX), Excel (XLSX), PowerPoint (PPTX), images and HTML. Tags are replaced inside the file and in the file name, so each recipient can get a personalised document.',
  },
  {
    q: 'Can I use EzyMailer for unsolicited bulk email?',
    a: 'No. You may only email people who have agreed to hear from you, and you must follow Google’s terms and the anti-spam laws that apply to you. Read our Acceptable Use Policy before you send.',
  },
  {
    q: 'macOS says the app can’t be opened. What do I do?',
    a: 'Right-click (or Control-click) EzyMailer in Applications and choose Open, then confirm. You only need to do this the first time.',
  },
  {
    q: 'Windows SmartScreen shows a warning. Is that normal?',
    a: 'It can appear for newly released apps. Click “More info”, then “Run anyway”. You can confirm the file is genuine by comparing its SHA-256 checksum with the one on our Download page.',
  },
];
