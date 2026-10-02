import { site } from '../config/site';

// Each document is a list of sections; a section has paragraphs (`p`) and an
// optional bullet list (`list`). Pages render these through LegalPage.
const n = site.companyName;

export const legalDocs = {
  terms: {
    title: 'Terms of Service',
    summary: `The agreement between you and ${n} when you use our website, desktop apps and services.`,
    sections: [
      {
        h: 'Acceptance of these terms',
        p: [
          `These Terms of Service ("Terms") govern your access to and use of the ${n} website, the ${n} desktop applications for Windows and macOS, and any related services (together, the "Service"). By downloading, installing, signing in to or otherwise using the Service you agree to these Terms. If you do not agree, do not use the Service.`,
          'If you use the Service on behalf of an organisation, you confirm that you have authority to bind that organisation and "you" refers to it.',
        ],
      },
      {
        h: 'Eligibility and accounts',
        p: ['You must be at least 18 years old and able to form a binding contract to use the Service.'],
        list: [
          'Accounts are issued by us or by your administrator and may be tied to a specific device.',
          'Accounts have a validity period. Access ends when the validity period expires unless renewed.',
          'You are responsible for keeping your credentials confidential and for all activity under your account.',
          'Tell us immediately at ' + site.supportEmail + ' if you suspect unauthorised use.',
        ],
      },
      {
        h: 'Licence',
        p: [
          `Subject to these Terms and the End User Licence Agreement, ${n} grants you a limited, non-exclusive, non-transferable, revocable licence to install and use the desktop app on devices registered to your account, for your internal business purposes.`,
        ],
      },
      {
        h: 'Your responsibilities',
        p: ['You are solely responsible for the email you send with the Service, including its content, its recipients and your legal basis for contacting them. In particular you agree to:'],
        list: [
          'Comply with our Acceptable Use Policy.',
          'Comply with the terms and policies of Google, Gmail and Google Cloud, and of any AI provider you connect.',
          'Comply with all applicable anti-spam, marketing, privacy and data-protection laws, such as the CAN-SPAM Act, GDPR, the UK GDPR, CASL and India’s Digital Personal Data Protection Act, 2023.',
          'Only email recipients who have given you permission or with whom you have another lawful basis to communicate.',
          'Honour unsubscribe and opt-out requests promptly.',
        ],
      },
      {
        h: 'Third-party services',
        p: [
          'The Service works with services we do not control, including Gmail, Google Cloud and AI providers such as OpenAI, Anthropic and DeepSeek. Your use of those services is governed by their own terms. We are not responsible for their availability, quotas, account actions (such as suspensions or sending limits) or changes to how they work.',
          'Changes made by third parties can affect or interrupt features of the Service. We will make reasonable efforts to adapt but do not guarantee continued compatibility.',
        ],
      },
      {
        h: 'Fees',
        p: [
          'Some access may require payment. Prices, billing periods and any refund terms will be shown to you before you buy. Unless stated otherwise or required by law, fees are non-refundable.',
        ],
      },
      {
        h: 'Intellectual property',
        p: [
          `The Service, including its software, design, logos and documentation, is owned by ${n} and its licensors and is protected by intellectual property laws. You keep all rights to the content you create with the Service.`,
        ],
      },
      {
        h: 'Suspension and termination',
        p: [
          'We may suspend or terminate your access at any time if you breach these Terms or the Acceptable Use Policy, if required by law, or if your use creates risk for us, other users or third parties. You may stop using the Service at any time.',
          'Sections that by their nature should survive termination — including responsibilities, disclaimers, limitation of liability and indemnity — will survive.',
        ],
      },
      {
        h: 'Disclaimer of warranties',
        p: [
          'THE SERVICE IS PROVIDED "AS IS" AND "AS AVAILABLE" WITHOUT WARRANTIES OF ANY KIND, WHETHER EXPRESS OR IMPLIED, INCLUDING WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NON-INFRINGEMENT. WE DO NOT WARRANT THAT EMAILS WILL BE DELIVERED, REACH THE INBOX, OR THAT THE SERVICE WILL BE UNINTERRUPTED OR ERROR-FREE.',
        ],
      },
      {
        h: 'Limitation of liability',
        p: [
          `TO THE MAXIMUM EXTENT PERMITTED BY LAW, ${n.toUpperCase()} WILL NOT BE LIABLE FOR ANY INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL OR PUNITIVE DAMAGES, OR FOR LOSS OF PROFITS, DATA, GOODWILL OR EMAIL ACCOUNTS. OUR TOTAL LIABILITY FOR ANY CLAIM RELATING TO THE SERVICE WILL NOT EXCEED THE AMOUNT YOU PAID US IN THE TWELVE MONTHS BEFORE THE CLAIM.`,
        ],
      },
      {
        h: 'Indemnity',
        p: [
          `You agree to indemnify and hold ${n} harmless from claims, losses and expenses (including reasonable legal fees) arising from your use of the Service, the content you send, or your breach of these Terms or of any law.`,
        ],
      },
      {
        h: 'Changes to these terms',
        p: [
          'We may update these Terms from time to time. If a change is material we will give reasonable notice, for example in the app or on this website. Continuing to use the Service after changes take effect means you accept the updated Terms.',
        ],
      },
      {
        h: 'Governing law',
        p: [
          `These Terms are governed by the laws of ${site.jurisdiction}, without regard to conflict-of-law rules. The courts of ${site.jurisdiction} have exclusive jurisdiction over any dispute, except where mandatory consumer law gives you the right to bring proceedings elsewhere.`,
        ],
      },
      {
        h: 'Contact',
        p: [`Questions about these Terms? Email ${site.legalEmail}.`],
      },
    ],
  },

  privacy: {
    title: 'Privacy Policy',
    summary: 'What we collect, why, where it lives, and the choices you have.',
    sections: [
      {
        h: 'Overview',
        p: [
          `This Privacy Policy explains how ${n} handles personal data when you visit our website or use the ${n} desktop apps and related services. We designed the app so that the material you work with — your Gmail sessions, recipient lists and campaign content — stays on your own computer wherever possible.`,
        ],
      },
      {
        h: 'Data we process on our servers',
        p: ['To run accounts and licences we process:'],
        list: [
          'Account data — username, password (stored hashed) and account validity dates.',
          'Device data — a device identifier used to enforce per-device licensing.',
          'Sign-in records — time and result of sign-in attempts.',
          'Usage records — app activity events (for example browser launched, campaign started) and daily totals of emails sent per account.',
          'Support correspondence — anything you send us when you contact us.',
        ],
      },
      {
        h: 'Data that stays on your device',
        p: ['The following is stored locally by the desktop app and is not uploaded to us as part of normal operation:'],
        list: [
          'Gmail browser sessions and cookies created in EzyMailer’s browser windows.',
          'Google OAuth credentials (client JSON and tokens) used for Gmail API mode.',
          'SMTP server settings and SMTP credentials (email addresses and passwords) you upload.',
          'Recipient lists, customer variables, subjects, bodies, attachments and tags.',
          'AI provider API keys you enter.',
        ],
      },
      {
        h: 'Third parties you choose to connect',
        p: [
          'When you send email, EzyMailer interacts with Gmail on your behalf through a browser window or the Gmail API, or connects directly to the SMTP server you configure. When you use AI features, the text you submit is sent directly to the AI provider you selected (OpenAI, Anthropic or DeepSeek) using your own API key. Those providers process the data under their own privacy policies.',
        ],
      },
      {
        h: 'Why we use your data',
        list: [
          'To authenticate you and enforce licence and device limits (performance of contract).',
          'To show your administrator usage and sending totals (legitimate interests / contract).',
          'To secure the Service, prevent abuse and investigate breaches of our policies (legitimate interests).',
          'To answer support requests (legitimate interests).',
          'To comply with legal obligations.',
        ],
      },
      {
        h: 'Google user data',
        p: [
          `${n}'s use of information received from Google APIs adheres to the Google API Services User Data Policy, including the Limited Use requirements. Gmail data accessed through the Gmail API is used only to send the messages you instruct the app to send and is not transferred to ${n}'s servers, sold, or used for advertising.`,
        ],
      },
      {
        h: 'Sharing',
        p: ['We do not sell personal data. We share it only with:'],
        list: [
          'Infrastructure providers that host our servers and database, under contract.',
          'Your organisation’s administrator, for accounts they manage.',
          'Authorities, where required by law or to protect rights and safety.',
        ],
      },
      {
        h: 'Retention',
        p: [
          'Account data is kept while your account is active and for a reasonable period afterwards. Sending statistics are kept as daily aggregates. Activity and history records may be periodically cleaned up. Data stored on your device remains until you delete it or uninstall the app.',
        ],
      },
      {
        h: 'Security',
        p: [
          'We use access controls, encrypted connections where supported and restricted database access to protect data on our servers. No system is perfectly secure, so please protect your device and credentials too.',
        ],
      },
      {
        h: 'Your rights',
        p: [
          `Depending on where you live, you may have the right to access, correct, delete or export your personal data, to object to or restrict certain processing, and to complain to a data-protection authority. To make a request, email ${site.privacyEmail}.`,
        ],
      },
      {
        h: 'Children',
        p: ['The Service is not directed to anyone under 18 and we do not knowingly collect their data.'],
      },
      {
        h: 'This website',
        p: [
          'Our website does not use advertising or third-party tracking cookies. Fonts are served by Google Fonts, which receives your IP address when the page loads. See our Cookie Policy for more.',
        ],
      },
      {
        h: 'Changes',
        p: ['We will post any changes to this policy on this page and update the effective date above.'],
      },
      {
        h: 'Contact',
        p: [`Privacy questions or requests: ${site.privacyEmail}.`],
      },
    ],
  },

  cookies: {
    title: 'Cookie Policy',
    summary: 'A short policy, because we use very few cookies.',
    sections: [
      {
        h: 'What cookies are',
        p: ['Cookies are small files a website stores in your browser. Similar technologies include local storage.'],
      },
      {
        h: 'Cookies on this website',
        p: [
          'This website does not set advertising, analytics or cross-site tracking cookies. It may use your browser’s local storage for strictly necessary preferences. Google Fonts may log technical request data when serving fonts.',
        ],
      },
      {
        h: 'Cookies in the desktop app',
        p: [
          'The EzyMailer browser windows store cookies from the sites you visit in them — mainly Google sign-in and Gmail — so that your sessions persist in Normal mode. These cookies remain on your computer. Incognito mode discards them when the window closes.',
        ],
      },
      {
        h: 'Managing cookies',
        p: [
          'You can clear or block cookies in your browser settings. In the app, use Reset or Incognito mode to start with a clean session.',
        ],
      },
      {
        h: 'Contact',
        p: [`Questions? Email ${site.privacyEmail}.`],
      },
    ],
  },

  acceptableUse: {
    title: 'Acceptable Use Policy',
    summary: 'EzyMailer is built for legitimate, permission-based email. Here is what that means.',
    sections: [
      {
        h: 'Permission first',
        p: [
          'You may only send email to people who have given you permission to contact them, or with whom you have another lawful basis for contact under the laws that apply to you and to them.',
        ],
      },
      {
        h: 'You must not use EzyMailer to',
        list: [
          'Send unsolicited bulk or commercial email (spam), or use purchased, rented, harvested or scraped address lists.',
          'Send phishing, malware, scams, fraudulent offers or deceptive content.',
          'Impersonate any person, brand or organisation, or forge headers or sender identity.',
          'Harass, threaten, defame or abuse anyone, or send hateful or illegal content.',
          'Infringe anyone’s intellectual property or privacy rights.',
          'Circumvent Google’s sending limits, abuse detection or terms of service, or create Google accounts in bulk to do so.',
          'Reverse-engineer, resell or share your EzyMailer account or licence.',
          'Attempt to access other users’ data or interfere with the Service.',
        ],
      },
      {
        h: 'Content requirements',
        list: [
          'Identify yourself accurately as the sender.',
          'Use subject lines that are not misleading.',
          'Include a working way to opt out of future messages where the law requires it, and honour opt-outs promptly.',
          'Include a valid physical postal address in commercial email where the law requires it.',
        ],
      },
      {
        h: 'Third-party rules',
        p: [
          'You must follow the Gmail Program Policies, Google Terms of Service, Google Cloud and Google API terms, and the policies of any AI provider you connect. Breaching them can lead to action against your Google account that we cannot reverse.',
        ],
      },
      {
        h: 'Enforcement',
        p: [
          'We may investigate suspected violations and suspend or terminate accounts without refund. Where appropriate we may cooperate with law enforcement.',
        ],
      },
      {
        h: 'Reporting abuse',
        p: [`If you have received abusive email you believe was sent with EzyMailer, contact ${site.supportEmail}.`],
      },
    ],
  },

  eula: {
    title: 'End User Licence Agreement',
    summary: 'The licence that applies to the EzyMailer desktop software.',
    sections: [
      {
        h: 'Grant of licence',
        p: [
          `${n} grants you a limited, non-exclusive, non-transferable, revocable licence to install and run the ${n} desktop software ("Software") on devices registered to your account, during your account’s validity period, in accordance with the Terms of Service.`,
        ],
      },
      {
        h: 'Restrictions',
        p: ['You must not:'],
        list: [
          'Copy, modify, or create derivative works of the Software except as permitted by law.',
          'Reverse-engineer, decompile or disassemble the Software except as permitted by law.',
          'Rent, lease, sell, sublicense or distribute the Software.',
          'Remove or alter any proprietary notices.',
          'Bypass licence, device or validity checks.',
        ],
      },
      {
        h: 'Third-party components',
        p: [
          'The Software includes third-party and open-source components, including a Chromium-based browser runtime, which are licensed under their own terms. Nothing in this agreement limits your rights under those licences.',
        ],
      },
      {
        h: 'Updates',
        p: [
          'We may provide updates. Some updates may be required to continue using the Software, for example to keep compatibility with Gmail or Google APIs.',
        ],
      },
      {
        h: 'Ownership',
        p: [`The Software is licensed, not sold. ${n} and its licensors retain all rights not expressly granted.`],
      },
      {
        h: 'Termination',
        p: [
          'This licence ends automatically if you breach it or when your account ends. On termination you must stop using and uninstall the Software.',
        ],
      },
      {
        h: 'Warranty and liability',
        p: ['The disclaimers and limitations of liability in the Terms of Service apply to the Software.'],
      },
    ],
  },

  disclaimer: {
    title: 'Disclaimer',
    summary: 'Important context about trademarks, deliverability and third-party services.',
    sections: [
      {
        h: 'Not affiliated with Google',
        p: [
          `${n} is an independent product. It is not affiliated with, endorsed by or sponsored by Google LLC. Gmail, Google Cloud and Chrome are trademarks of Google LLC. OpenAI, Anthropic and DeepSeek are trademarks of their respective owners.`,
        ],
      },
      {
        h: 'No delivery guarantee',
        p: [
          'Email delivery depends on many factors outside our control, including recipient servers, spam filters, sender reputation and provider limits. We make no promises about delivery rates or inbox placement.',
        ],
      },
      {
        h: 'Your account, your responsibility',
        p: [
          'Gmail and Google Cloud may limit, suspend or close accounts that breach their policies. You are responsible for how you use your accounts with EzyMailer.',
        ],
      },
      {
        h: 'Not legal advice',
        p: [
          'Information on this website about email laws and best practice is general information, not legal advice. Consult a qualified professional about your obligations.',
        ],
      },
    ],
  },
};

export const legalLinks = [
  { to: '/terms', label: 'Terms of Service' },
  { to: '/privacy', label: 'Privacy Policy' },
  { to: '/cookies', label: 'Cookie Policy' },
  { to: '/acceptable-use', label: 'Acceptable Use' },
  { to: '/eula', label: 'EULA' },
  { to: '/disclaimer', label: 'Disclaimer' },
];
