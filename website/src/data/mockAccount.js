// DESIGN ONLY — sample data for the account area. Nothing here is real;
// replace with API calls when the account backend is wired up.

export const user = {
  name: 'Alex Morgan',
  username: 'alex',
  email: 'user@example.com',
  phone: '+91 98765 43210',
  company: 'Acme Outreach',
  country: 'India',
  joined: '2026-03-14',
  avatarInitials: 'AM',
};

export const license = {
  key: 'EZM-7F3K-92QD-LX4P',
  plan: 'Pro',
  status: 'Active',
  startDate: '2026-07-02',
  endDate: '2026-11-02',
  daysLeft: 31,
  totalDays: 123,
  devicesAllowed: 1,
  device: { name: 'MacBook Pro', os: 'macOS 15', id: 'MAC-8C2F…A91E', boundOn: '2026-07-02' },
  sentToday: 842,
  sentThisMonth: 18450,
};

export const plans = [
  { id: 'm1', months: 1, label: '1 Month', price: '₹1,499', perMonth: '₹1,499 / mo' },
  { id: 'm3', months: 3, label: '3 Months', price: '₹3,999', perMonth: '₹1,333 / mo', tag: 'Popular' },
  { id: 'm6', months: 6, label: '6 Months', price: '₹7,499', perMonth: '₹1,250 / mo' },
  { id: 'm12', months: 12, label: '12 Months', price: '₹13,999', perMonth: '₹1,167 / mo', tag: 'Best value' },
];

export const sentLast14 = [610, 720, 540, 880, 930, 410, 260, 790, 860, 1020, 940, 700, 380, 842];

export const loginLogs = [
  { id: 1, time: '2026-10-02 09:14', device: 'MacBook Pro', app: 'Desktop · macOS', ip: '103.21.xx.xx', location: 'Kolkata, IN', status: 'Success' },
  { id: 2, time: '2026-10-01 18:42', device: 'Chrome · macOS', app: 'Website', ip: '103.21.xx.xx', location: 'Kolkata, IN', status: 'Success' },
  { id: 3, time: '2026-10-01 08:57', device: 'MacBook Pro', app: 'Desktop · macOS', ip: '103.21.xx.xx', location: 'Kolkata, IN', status: 'Success' },
  { id: 4, time: '2026-09-30 22:03', device: 'Windows PC', app: 'Desktop · Windows', ip: '49.37.xx.xx', location: 'Delhi, IN', status: 'Blocked · device limit' },
  { id: 5, time: '2026-09-30 09:20', device: 'MacBook Pro', app: 'Desktop · macOS', ip: '103.21.xx.xx', location: 'Kolkata, IN', status: 'Success' },
  { id: 6, time: '2026-09-29 11:46', device: 'Safari · iPhone', app: 'Website', ip: '106.51.xx.xx', location: 'Kolkata, IN', status: 'Failed · wrong password' },
  { id: 7, time: '2026-09-29 09:02', device: 'MacBook Pro', app: 'Desktop · macOS', ip: '103.21.xx.xx', location: 'Kolkata, IN', status: 'Success' },
  { id: 8, time: '2026-09-28 10:31', device: 'MacBook Pro', app: 'Desktop · macOS', ip: '103.21.xx.xx', location: 'Kolkata, IN', status: 'Success' },
];

export const renewals = [
  { id: 'INV-2026-0712', date: '2026-07-02', plan: 'Pro · 4 Months', period: '2026-07-02 → 2026-11-02', amount: '₹5,299', method: 'UPI', status: 'Paid' },
  { id: 'INV-2026-0601', date: '2026-06-01', plan: 'Pro · 1 Month', period: '2026-06-02 → 2026-07-02', amount: '₹1,499', method: 'Card •••• 4821', status: 'Paid' },
  { id: 'INV-2026-0331', date: '2026-03-14', plan: 'Starter · 3 Months', period: '2026-03-14 → 2026-06-02', amount: '₹3,499', method: 'UPI', status: 'Paid' },
  { id: 'INV-2026-0314', date: '2026-03-14', plan: 'Trial', period: '2026-03-14 → 2026-03-14', amount: '₹0', method: '—', status: 'Converted' },
];

export const updateCategories = [
  { id: 'app', label: 'App updates' },
  { id: 'rules', label: 'Rules' },
  { id: 'google', label: 'Google updates' },
  { id: 'news', label: 'News' },
];

export const updates = [
  { id: 12, cat: 'app', date: '2026-10-02', title: 'SMTP sending mode', tag: 'Release', body: 'Send through any SMTP server. Upload credentials from CSV or Excel (download the Sample file), set server, port and security with the ⚙ button, and choose each sender’s name.', pinned: true },
  { id: 13, cat: 'app', date: '2026-10-02', title: 'Start, Stop and Try for every sender', tag: 'Release', body: 'Each Gmail window, API account and SMTP credential can be started, stopped and tested on its own. Try sends a real test email; the red ! shows any server error.' },
  { id: 14, cat: 'app', date: '2026-10-02', title: 'One Per sender limit, sender names for Gmail API', tag: 'Improvement', body: 'Per sender limit now applies to Manual, Gmail API and SMTP and matches Settings. Gmail API accounts can use their Google name, a fixed random name or your own.' },
  { id: 15, cat: 'app', date: '2026-10-02', title: 'One million $name values on Windows', tag: 'Improvement', body: '$name, $fullname, $city and $word tags now have the same large pools on Windows as on macOS. $email and $url produce realistic values.' },
  { id: 1, cat: 'app', date: '2026-09-29', title: 'v1.0.0 — $dictionary tag & PDF export', tag: 'Release', body: 'New $dictionary tag inserts real words from a built-in dictionary. Download any preview as a PDF. Fixed the Windows preview window.' },
  { id: 2, cat: 'app', date: '2026-09-26', title: 'Gmail API: sign in yourself', tag: 'Improvement', body: 'Leave the password blank in Gmail API Automation to complete Google sign-in manually. Every setup step is now shown as it runs.' },
  { id: 3, cat: 'app', date: '2026-09-21', title: 'Faster, more reliable Console automation', tag: 'Fix', body: 'Recovers from 403 access_denied at the consent screen and keeps the window open if JSON creation fails.' },
  { id: 4, cat: 'rules', date: '2026-09-15', title: 'Per-sender daily limit guidance', tag: 'Rule', body: 'Keep each Gmail account well under Google’s daily sending limits. We recommend starting new accounts low and increasing gradually.', pinned: true },
  { id: 5, cat: 'rules', date: '2026-08-30', title: 'Permission-based sending only', tag: 'Policy', body: 'Sending to purchased or scraped lists breaks our Acceptable Use Policy and can lead to account suspension.' },
  { id: 6, cat: 'rules', date: '2026-08-20', title: 'One device per licence', tag: 'Rule', body: 'Each licence is bound to one device. Contact support to move your licence to a new computer.' },
  { id: 7, cat: 'google', date: '2026-09-24', title: 'Bulk sender requirements reminder', tag: 'Google', body: 'Google requires SPF/DKIM authentication, easy unsubscribe and low spam rates for senders of large volumes to Gmail.' },
  { id: 8, cat: 'google', date: '2026-09-10', title: 'Cloud Console now asks for 2-Step Verification', tag: 'Google', body: 'Google Cloud requires 2-Step Verification on the account before projects can be created. Turn it on before running Gmail API setup.' },
  { id: 9, cat: 'google', date: '2026-08-28', title: 'OAuth client picker change', tag: 'Google', body: 'Newly created projects can take a moment to appear in the project search. Use the “Recent” tab if it is missing.' },
  { id: 10, cat: 'news', date: '2026-09-29', title: 'Website and account portal launched', tag: 'News', body: 'Manage your licence, renewals and login history from the new account portal.' },
  { id: 11, cat: 'news', date: '2026-09-01', title: 'Telegram support channel is live', tag: 'News', body: 'Chat with the team directly on Telegram for faster help.' },
];
