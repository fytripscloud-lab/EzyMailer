import WebStoriesRounded from '@mui/icons-material/WebStoriesRounded';
import ApiRounded from '@mui/icons-material/ApiRounded';
import BoltRounded from '@mui/icons-material/BoltRounded';
import GroupsRounded from '@mui/icons-material/GroupsRounded';
import ViewQuiltRounded from '@mui/icons-material/ViewQuiltRounded';
import AttachFileRounded from '@mui/icons-material/AttachFileRounded';
import SellRounded from '@mui/icons-material/SellRounded';
import AutoAwesomeRounded from '@mui/icons-material/AutoAwesomeRounded';
import PreviewRounded from '@mui/icons-material/PreviewRounded';
import TuneRounded from '@mui/icons-material/TuneRounded';
import InsightsRounded from '@mui/icons-material/InsightsRounded';
import HistoryRounded from '@mui/icons-material/HistoryRounded';
import ShieldRounded from '@mui/icons-material/ShieldRounded';
import DevicesRounded from '@mui/icons-material/DevicesRounded';
import DnsRounded from '@mui/icons-material/DnsRounded';
import PlayCircleRounded from '@mui/icons-material/PlayCircleRounded';
import BadgeRounded from '@mui/icons-material/BadgeRounded';

export const categories = ['All', 'Sending', 'Content', 'Intelligence', 'Control'];

export const features = [
  {
    id: 'multi-window',
    icon: WebStoriesRounded,
    category: 'Sending',
    color: '#1EE8FF',
    title: 'Multi-Window Sending Engine',
    short: 'Run many isolated Gmail sessions side by side and spread a campaign across all of them.',
    points: [
      'Launch a fleet of browser windows with one click — staggered so your machine stays responsive',
      'Incognito mode for clean, profile-free sessions or Normal mode to keep saved logins',
      'Auto-tiling Layout presets arrange every window on screen',
      'Pause, Reset, Default and Clear controls for the whole fleet',
      'Bundled Chromium runtime — no separate browser install required',
    ],
  },
  {
    id: 'gmail-api',
    icon: ApiRounded,
    category: 'Sending',
    color: '#8B5CF6',
    title: 'Gmail API Mode',
    short: 'Send through the official Gmail API with a guided setup that does the Cloud Console work for you.',
    points: [
      'Guided automation creates the Cloud project, enables the Gmail API and builds the OAuth client',
      'Each Gmail account owns its own Cloud project — quotas never collide',
      'Upload an existing credentials JSON, or let EzyMailer generate one',
      'One-click Login walks through the full Google consent flow',
      'Choose the sender name: the Google account name, a fixed random name, or your own',
      'Per sender limit caps how many emails each account sends',
    ],
  },
  {
    id: 'smtp',
    icon: DnsRounded,
    category: 'Sending',
    color: '#FFB547',
    title: 'SMTP Sending',
    short: 'Send from any SMTP server — Gmail App Passwords, Workspace, or your own mail host — with no browser at all.',
    points: [
      'Server, port and security (Auto, SSL, TLS, TLS when available or none) in one settings dialog',
      'Upload credentials as CSV or Excel (.xlsx / .xls) — download the Sample file for the format',
      'Each credential is its own sending lane with a reused, encrypted connection',
      'A credential with a rejected login or a hit daily limit stops on its own; the rest keep going',
      'Per sender limit and Sender Name per credential',
    ],
  },
  {
    id: 'session-control',
    icon: PlayCircleRounded,
    category: 'Sending',
    color: '#3DFFA8',
    title: 'Per-Session Control & Test Emails',
    short: 'Start, stop and test every sender individually — Gmail windows, API accounts and SMTP credentials alike.',
    points: [
      'Start one sender on its own, or add more while a campaign is already running',
      'Stop pauses just that sender; the others take over the remaining emails',
      'Try sends a test email from that sender, with your real subject, body, attachment and tags',
      'Red ! button opens the exact error from the server for anything that failed',
      'One shared queue: no recipient is ever sent twice, and Done turns green when a sender finishes',
    ],
  },
  {
    id: 'fast-compose',
    icon: BoltRounded,
    category: 'Sending',
    color: '#3DFFA8',
    title: 'Fast Compose',
    short: 'Reuse one warm Gmail tab with inline Compose — no page reloads between messages.',
    points: [
      'Keeps a single Gmail tab hot and fills the inline Compose window',
      'Restores minimised Compose windows automatically',
      'Confirms every field and click before moving on — fast, never sloppy',
      'On by default, switchable per campaign',
    ],
  },
  {
    id: 'recipients',
    icon: GroupsRounded,
    category: 'Content',
    color: '#4DA3FF',
    title: 'Smart Recipient Data',
    short: 'Paste or import your list, then validate, de-duplicate and count it in one pass.',
    points: [
      'Load recipients from a file or paste them directly',
      'Validate & Count reports valid, invalid and duplicate addresses',
      'Domain filter — Gmail-only or every allowed domain',
      'Per-recipient customer variables (name, company, city…) for personalisation',
    ],
  },
  {
    id: 'subject-body',
    icon: ViewQuiltRounded,
    category: 'Content',
    color: '#FF4FD8',
    title: 'Subject & Multi-Body Studio',
    short: 'Write many subject lines and body variants, each in its own named tab.',
    points: [
      'Unlimited body tabs with custom labels',
      'Plain text, HTML or template mode per body',
      'Import subjects and bodies from CSV in bulk',
      'Upload HTML or CSV bodies — the first file fills Body 1, more files open new tabs',
    ],
  },
  {
    id: 'attachments',
    icon: AttachFileRounded,
    category: 'Content',
    color: '#FFB547',
    title: 'Attachment Studio',
    short: 'Design an attachment once and EzyMailer renders a personalised file for every recipient.',
    points: [
      'Rich text editor — fonts, sizes, colours, alignment, lists, embedded images',
      'Or switch to raw HTML Code mode for pixel-perfect control',
      'Convert to PDF, Word (DOCX), Excel (XLSX), PowerPoint (PPTX) or image',
      'Tags work inside the file and in its file name',
      'Upload HTML designs — the first goes into Content 1, the rest open new tabs',
    ],
  },
  {
    id: 'tags',
    icon: SellRounded,
    category: 'Intelligence',
    color: '#1EE8FF',
    title: 'Dynamic Tags & $dictionary',
    short: 'Placeholders that turn every message into a one-of-one, replaced at send time.',
    points: [
      'Dynamic tags generate fresh random values for each email',
      '$name / $fullname: one million name combinations, the same on Windows and macOS',
      '$spanishname (~15 million), $city, $email, $url and 464,000-word $dictionary',
      'Manual custom tags for your own key/value pairs',
      'Replaced in subject, body, attachment content and attachment file name',
      'Regenerate All, Reset to Default, or Generate with AI',
    ],
  },
  {
    id: 'sender-names',
    icon: BadgeRounded,
    category: 'Intelligence',
    color: '#FF4FD8',
    title: 'Sender Identities',
    short: 'Decide the name recipients see in their inbox — per SMTP credential and per Gmail API account.',
    points: [
      'Auto: each sender gets one realistic random name and keeps it for every campaign',
      'Auto (Random Name): a fresh name every campaign',
      '$fullname or $spanishname for themed names, or Custom for your own',
      'Gmail API accounts can keep their real Google account name',
    ],
  },
  {
    id: 'ai',
    icon: AutoAwesomeRounded,
    category: 'Intelligence',
    color: '#8B5CF6',
    title: 'AI Writing Assistant',
    short: 'Bring your own key and let AI draft subjects, bodies, tags and even redesign your HTML.',
    points: [
      'Works with OpenAI, Anthropic and DeepSeek',
      'Choose the model and see live connection status',
      'Generate subject lines, body copy and tag values',
      'AI-assisted redesign right inside the HTML preview',
    ],
  },
  {
    id: 'preview',
    icon: PreviewRounded,
    category: 'Content',
    color: '#3DFFA8',
    title: 'Live Preview & PDF Export',
    short: 'See exactly what your recipient will see before a single email leaves.',
    points: [
      'Dedicated preview window for bodies and attachments',
      'Reload, zoom and raw-source views',
      'Download the rendered preview as a PDF',
    ],
  },
  {
    id: 'controls',
    icon: TuneRounded,
    category: 'Control',
    color: '#4DA3FF',
    title: 'Precision Sending Controls',
    short: 'Pace, distribute and retry exactly the way you want.',
    points: [
      'One Per sender limit shared by Manual, Gmail API and SMTP — warns before you exceed capacity',
      'Delay between emails (fixed, automatic or human-like) and automatic retries',
      'Choose recipient order and parallel or sequential sending',
      'Optional proxy support and startup tabs',
      'Auto-delete from Sent after delivery',
    ],
  },
  {
    id: 'dashboard',
    icon: InsightsRounded,
    category: 'Control',
    color: '#FF4FD8',
    title: 'Live Campaign Dashboard',
    short: 'Watch every window, every send and every retry in real time.',
    points: [
      'Every sender shows Ready, Sending, Stopped, Done or Failed with sent / expected counts',
      'Campaign progress bar with live refresh',
      'Detailed send log of successes, failures and retries',
      'Start Campaign tells you exactly what is missing — and which tab to fix it in',
      'Sending mode is locked while a campaign runs, so nothing switches mid-send',
    ],
  },
  {
    id: 'activity',
    icon: HistoryRounded,
    category: 'Control',
    color: '#FFB547',
    title: 'Activity Log',
    short: 'A complete, timestamped trail of everything the app does.',
    points: [
      'Logins, browser launches, file loads, campaign starts and results',
      'Perfect for debugging and accountability',
      'Toast notifications for the things that need your attention',
    ],
  },
  {
    id: 'secure',
    icon: ShieldRounded,
    category: 'Control',
    color: '#3DFFA8',
    title: 'Secure Licensed Accounts',
    short: 'Device-aware sign-in with licence validity managed from a central admin portal.',
    points: [
      'Sign in with your EzyMailer account',
      'Device restriction and validity checks on every login',
      'Daily sent-email counts available to your admin',
      'Your Gmail sessions and credentials stay on your machine',
    ],
  },
  {
    id: 'cross-platform',
    icon: DevicesRounded,
    category: 'Control',
    color: '#1EE8FF',
    title: 'Native on Windows & macOS',
    short: 'One product, two first-class desktop apps.',
    points: [
      'Signed-in experience is identical on both platforms',
      'Packaged with its own browser runtime',
      'Dark, editor-inspired interface built for long sessions',
    ],
  },
];

export const steps = [
  { n: '01', title: 'Load', text: 'Import your recipient list, validate it and strip duplicates in seconds.' },
  { n: '02', title: 'Compose', text: 'Write subjects and body variants, design an attachment, and preview it live.' },
  { n: '03', title: 'Personalise', text: 'Drop in tags, $dictionary words and customer variables — or let AI write them.' },
  { n: '04', title: 'Launch', text: 'Test with Try, then start every sender at once — or one by one — over Gmail, the Gmail API or SMTP.' },
];
