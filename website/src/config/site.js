// Central place for everything that changes between releases or deployments.
// Point the download URLs at wherever the installers are hosted (S3, GitHub
// Releases, or files dropped into public/downloads/ for a same-origin host).
export const site = {
  name: 'EzyMailer',
  tagline: 'Campaigns at light speed.',
  version: '1.0.0',
  releaseDate: '2026-10-02',
  supportEmail: 'support@ezymailer.com',
  // Chat button target. Replace with your real Telegram username or group invite link.
  telegramUrl: 'https://t.me/ezymailer',
  legalEmail: 'legal@ezymailer.com',
  privacyEmail: 'privacy@ezymailer.com',
  companyName: 'EzyMailer',
  jurisdiction: 'India',
  legalEffectiveDate: 'October 2, 2026',
  downloads: {
    windows: {
      label: 'Windows',
      url: '/downloads/EzyMailer-Windows.exe',
      fileName: 'EzyMailer-Windows.exe',
      size: '109 MB',
      requirements: ['Windows 10 or 11 (64-bit)', '16 GB RAM minimum (32 GB recommended)', '10 GB free disk space', 'Internet connection'],
      sha256: '8c22e4954c9a2b960a4e964678b96a258563e72a5baa606ad7220265a79b6a3f',
    },
    mac: {
      label: 'macOS',
      url: '/downloads/EzyMailer-macOS.dmg',
      fileName: 'EzyMailer-macOS.dmg',
      size: '116 MB',
      requirements: ['macOS 12 Monterey or later', 'Apple silicon or Intel', '16 GB RAM minimum (32 GB recommended)', '10 GB free disk space'],
      sha256: '6be1e4d360b8c26925bbf8437b87f8be3682e4caed261c125adcd17de09d9af5',
    },
  },
};
