import { useEffect, useState } from 'react';
import { Link as RouterLink } from 'react-router-dom';
import Box from '@mui/material/Box';
import Container from '@mui/material/Container';
import Grid from '@mui/material/Grid';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import Stack from '@mui/material/Stack';
import Chip from '@mui/material/Chip';
import { alpha } from '@mui/material/styles';
import ArrowForwardRounded from '@mui/icons-material/ArrowForwardRounded';
import CheckCircleRounded from '@mui/icons-material/CheckCircleRounded';
import Apple from '@mui/icons-material/Apple';
import Microsoft from '@mui/icons-material/Microsoft';
import AppMockup from '../components/AppMockup';
import DownloadButtons from '../components/DownloadButtons';
import SectionHeading from '../components/SectionHeading';
import GlassCard from '../components/GlassCard';
import Reveal from '../components/Reveal';
import { features, steps } from '../data/features';
import { gradientText, neon } from '../theme';

const mono = '"JetBrains Mono", monospace';

function Hero() {
  return (
    <Box sx={{ position: 'relative', pt: { xs: 6, md: 10 }, pb: { xs: 8, md: 12 } }}>
      <Container maxWidth="lg">
        <Grid container spacing={{ xs: 7, md: 6 }} sx={{ alignItems: 'center' }}>
          <Grid size={{ xs: 12, md: 6 }}>
            <Reveal>
              <Chip
                icon={<Box component="span" sx={{ width: 8, height: 8, borderRadius: '50%', bgcolor: neon.green, boxShadow: `0 0 10px ${neon.green}`, ml: '10px !important' }} />}
                label="New · SMTP sending + Start / Stop / Try per sender"
                component={RouterLink}
                to="/features#session-control"
                clickable
                sx={{ mb: 3, bgcolor: alpha(neon.cyan, 0.06), border: `1px solid ${alpha(neon.cyan, 0.25)}`, color: 'text.primary' }}
              />
            </Reveal>
            <Reveal delay={80}>
              <Typography variant="h1" sx={{ fontSize: { xs: '2.9rem', sm: '3.8rem', md: '4.6rem' } }}>
                Every inbox.{' '}
                <Box component="span" sx={{ ...gradientText, display: 'inline-block' }}>One-of-one.</Box>
                <br />
                At light speed.
              </Typography>
            </Reveal>
            <Reveal delay={160}>
              <Typography color="text.secondary" sx={{ mt: 3, fontSize: { xs: '1.05rem', md: '1.2rem' }, lineHeight: 1.7, maxWidth: 540 }}>
                EzyMailer is the desktop command center for email campaigns. Send through a fleet of Gmail windows, the official
                Gmail API or any SMTP server, personalise every subject, body and attachment with dynamic tags and AI, and start,
                stop or test every sender on its own.
              </Typography>
            </Reveal>
            <Reveal delay={240} sx={{ mt: 4.5 }}>
              <DownloadButtons />
            </Reveal>
            <Reveal delay={320}>
              <Stack direction="row" spacing={2.5} sx={{ mt: 3, color: 'text.secondary', fontSize: 13, flexWrap: 'wrap', rowGap: 1 }}>
                {['Windows 10 / 11', 'macOS 12+', 'Browser runtime included'].map((t) => (
                  <Box key={t} sx={{ display: 'flex', alignItems: 'center', gap: 0.75 }}>
                    <CheckCircleRounded sx={{ fontSize: 16, color: neon.cyan }} /> {t}
                  </Box>
                ))}
              </Stack>
            </Reveal>
          </Grid>
          <Grid size={{ xs: 12, md: 6 }}>
            <Reveal delay={200}>
              <AppMockup />
            </Reveal>
          </Grid>
        </Grid>
      </Container>
    </Box>
  );
}

function Marquee() {
  const items = ['Multi-window sending', 'Gmail API', 'SMTP', 'Start · Stop · Try per sender', 'Per sender limit', 'Sender names', 'PDF · DOCX · XLSX · PPTX', '1M-name dynamic tags', 'AI writing', 'Live preview', 'Retry engine', 'Windows', 'macOS'];
  const row = [...items, ...items];
  return (
    <Box sx={{ borderBlock: `1px solid ${neon.line}`, py: 2.5, overflow: 'hidden', bgcolor: alpha('#0B1020', 0.4), maskImage: 'linear-gradient(90deg, transparent, #000 10%, #000 90%, transparent)', WebkitMaskImage: 'linear-gradient(90deg, transparent, #000 10%, #000 90%, transparent)' }}>
      <Box sx={{ display: 'flex', width: 'max-content', animation: 'marquee 40s linear infinite' }}>
        {row.map((t, i) => (
          <Box key={i} sx={{ display: 'flex', alignItems: 'center', gap: 3, px: 3, fontFamily: mono, fontSize: 14, color: 'text.secondary', whiteSpace: 'nowrap' }}>
            {t}
            <Box component="span" sx={{ color: neon.cyan }}>✦</Box>
          </Box>
        ))}
      </Box>
    </Box>
  );
}

function Stats() {
  const stats = [
    { v: '3', l: 'Sending engines', s: 'Gmail windows, Gmail API or SMTP' },
    { v: '6', l: 'Attachment formats', s: 'PDF, DOCX, XLSX, PPTX, image, HTML' },
    { v: '3', l: 'AI providers', s: 'OpenAI, Anthropic, DeepSeek' },
    { v: '1M', l: 'Name combinations', s: '$name / $fullname on every platform' },
  ];
  return (
    <Container maxWidth="lg" sx={{ py: { xs: 8, md: 12 } }}>
      <Grid container spacing={2.5}>
        {stats.map((s, i) => (
          <Grid key={s.l} size={{ xs: 6, md: 3 }}>
            <Reveal delay={i * 80} sx={{ height: '100%' }}>
              <GlassCard sx={{ textAlign: 'center', p: { xs: 2.5, md: 3.5 } }}>
                <Typography sx={{ ...gradientText, fontFamily: '"Space Grotesk"', fontWeight: 700, fontSize: { xs: 44, md: 60 }, lineHeight: 1 }}>{s.v}</Typography>
                <Typography sx={{ fontWeight: 600, mt: 1.5 }}>{s.l}</Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>{s.s}</Typography>
              </GlassCard>
            </Reveal>
          </Grid>
        ))}
      </Grid>
    </Container>
  );
}

function HowItWorks() {
  return (
    <Container maxWidth="lg" sx={{ py: { xs: 8, md: 12 } }}>
      <SectionHeading eyebrow="How it works" title="From list to launch in" highlight="four moves." subtitle="Everything you need lives in one window. No spreadsheets glued to scripts glued to browser tabs." />
      <Grid container spacing={2.5} sx={{ position: 'relative' }}>
        <Box aria-hidden sx={{ display: { xs: 'none', md: 'block' }, position: 'absolute', top: 54, left: '12%', right: '12%', height: 2, background: `linear-gradient(90deg, transparent, ${neon.cyan}, ${neon.violet}, transparent)`, opacity: 0.4 }} />
        {steps.map((s, i) => (
          <Grid key={s.n} size={{ xs: 12, sm: 6, md: 3 }}>
            <Reveal delay={i * 100} sx={{ height: '100%' }}>
              <GlassCard>
                <Box sx={{ width: 52, height: 52, borderRadius: 3, display: 'grid', placeItems: 'center', fontFamily: mono, fontWeight: 600, color: neon.cyan, border: `1px solid ${alpha(neon.cyan, 0.4)}`, bgcolor: alpha(neon.cyan, 0.08), boxShadow: `0 0 30px -6px ${alpha(neon.cyan, 0.6)}`, mb: 2.5 }}>
                  {s.n}
                </Box>
                <Typography variant="h5" sx={{ mb: 1 }}>{s.title}</Typography>
                <Typography color="text.secondary" sx={{ lineHeight: 1.7 }}>{s.text}</Typography>
              </GlassCard>
            </Reveal>
          </Grid>
        ))}
      </Grid>
    </Container>
  );
}

function FeatureBento() {
  const pick = ['smtp', 'session-control', 'gmail-api', 'multi-window', 'tags', 'attachments'];
  const items = pick.map((id) => features.find((f) => f.id === id));
  const spans = [7, 5, 5, 7, 6, 6];
  return (
    <Container maxWidth="lg" sx={{ py: { xs: 8, md: 12 } }}>
      <SectionHeading eyebrow="Features" title="A full campaign studio," highlight="not a script." subtitle={`${features.length} tightly integrated modules, designed to work together from the first import to the last send.`} />
      <Grid container spacing={2.5}>
        {items.map((f, i) => {
          const Icon = f.icon;
          return (
            <Grid key={f.id} size={{ xs: 12, md: spans[i] }}>
              <Reveal delay={(i % 2) * 100} sx={{ height: '100%' }}>
                <GlassCard glow={f.color} sx={{ overflow: 'hidden', p: { xs: 3, md: 4 } }}>
                  <Box aria-hidden sx={{ position: 'absolute', top: -80, right: -80, width: 220, height: 220, borderRadius: '50%', background: `radial-gradient(circle, ${alpha(f.color, 0.25)}, transparent 70%)` }} />
                  <Box sx={{ width: 48, height: 48, borderRadius: 3, display: 'grid', placeItems: 'center', bgcolor: alpha(f.color, 0.12), border: `1px solid ${alpha(f.color, 0.35)}`, color: f.color, mb: 2.5 }}>
                    <Icon />
                  </Box>
                  <Typography variant="h5" sx={{ mb: 1 }}>{f.title}</Typography>
                  <Typography color="text.secondary" sx={{ lineHeight: 1.7, mb: 2 }}>{f.short}</Typography>
                  <Stack spacing={0.75}>
                    {f.points.slice(0, 3).map((p) => (
                      <Box key={p} sx={{ display: 'flex', gap: 1, fontSize: 14, color: 'text.secondary' }}>
                        <Box component="span" sx={{ color: f.color }}>→</Box>
                        {p}
                      </Box>
                    ))}
                  </Stack>
                </GlassCard>
              </Reveal>
            </Grid>
          );
        })}
      </Grid>
      <Box sx={{ textAlign: 'center', mt: 5 }}>
        <Button component={RouterLink} to="/features" variant="outlined" size="large" endIcon={<ArrowForwardRounded />}>
          Explore all features
        </Button>
      </Box>
    </Container>
  );
}


const engines = [
  {
    t: 'Gmail windows', c: neon.cyan, tag: 'Manual',
    d: 'Drives real Gmail tabs, just like you would by hand. Great for accounts you already use in the browser.',
    p: ['Many windows, many tabs', 'Incognito or saved logins', 'Fast Compose reuses a warm tab'],
  },
  {
    t: 'Gmail API', c: neon.violet, tag: 'API JSON',
    d: 'Sends through Google’s official API. EzyMailer sets up the Cloud project and OAuth client for you.',
    p: ['No browser while sending', 'Google account name or your own', 'One Cloud project per account'],
  },
  {
    t: 'SMTP', c: '#FFB547', tag: 'SMTP',
    d: 'Any mail server: Gmail App Passwords, Google Workspace or your own host. Upload credentials from CSV or Excel.',
    p: ['SSL, TLS or automatic security', 'One lane per credential', 'Bad logins stop on their own'],
  },
];

function Engines() {
  return (
    <Container maxWidth="lg" sx={{ py: { xs: 8, md: 12 } }}>
      <SectionHeading eyebrow="Sending modes" title="Three engines," highlight="one control panel." subtitle="Pick how mail leaves the building. The same personalisation, limits, retries and live controls work in every mode." />
      <Grid container spacing={2.5}>
        {engines.map((e, i) => (
          <Grid key={e.t} size={{ xs: 12, md: 4 }}>
            <Reveal delay={i * 100} sx={{ height: '100%' }}>
              <GlassCard glow={e.c}>
                <Chip label={e.tag} size="small" sx={{ mb: 2, color: e.c, bgcolor: alpha(e.c, 0.1), border: `1px solid ${alpha(e.c, 0.35)}` }} />
                <Typography variant="h5" sx={{ mb: 1 }}>{e.t}</Typography>
                <Typography color="text.secondary" sx={{ lineHeight: 1.7, mb: 2 }}>{e.d}</Typography>
                <Stack spacing={0.75}>
                  {e.p.map((x) => (
                    <Box key={x} sx={{ display: 'flex', gap: 1, fontSize: 14, color: 'text.secondary' }}>
                      <CheckCircleRounded sx={{ fontSize: 16, color: e.c, mt: '2px' }} />
                      {x}
                    </Box>
                  ))}
                </Stack>
              </GlassCard>
            </Reveal>
          </Grid>
        ))}
      </Grid>
    </Container>
  );
}

const sessionFrames = [
  [['Sending', 12, 40], ['Sending', 9, 40], ['Ready', 0, 0]],
  [['Stopped', 14, 40], ['Sending', 18, 40], ['Sending', 3, 40]],
  [['Sending', 17, 40], ['Sending', 27, 40], ['Failed', 0, 1]],
  [['Done', 40, 40], ['Done', 40, 40], ['Failed', 0, 1]],
];
const sessionRows = ['Window 1 · Gmail', 'sales@yourcompany.com', 'news@mailhost.io'];
const statusColor = { Sending: '#4fc1ff', Stopped: '#d7ba7d', Done: '#89d185', Failed: '#f48771', Ready: '#9e9e9e' };

function SessionSpotlight() {
  const [f, setF] = useState(0);
  useEffect(() => {
    if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) return undefined;
    const id = setInterval(() => setF((v) => (v + 1) % sessionFrames.length), 1800);
    return () => clearInterval(id);
  }, []);
  const btn = (label, bg, fg) => (
    <Box component="span" sx={{ px: 1, py: 0.25, borderRadius: 1, fontSize: 11, fontWeight: 700, bgcolor: bg, color: fg }}>{label}</Box>
  );
  return (
    <Container maxWidth="lg" sx={{ py: { xs: 8, md: 12 } }}>
      <Grid container spacing={{ xs: 5, md: 8 }} sx={{ alignItems: 'center' }}>
        <Grid size={{ xs: 12, md: 6 }}>
          <SectionHeading align="left" eyebrow="Active sessions" title="Every sender," highlight="under your thumb." subtitle="Start one sender on its own or add more mid-campaign. Stop pauses just that sender while the others pick up its share. Try fires a real test email first, and the red ! shows the exact server error when something fails." />
          <Button component={RouterLink} to="/features#session-control" endIcon={<ArrowForwardRounded />} sx={{ mt: -3, color: neon.green }}>
            How per-session control works
          </Button>
        </Grid>
        <Grid size={{ xs: 12, md: 6 }}>
          <Reveal>
            <GlassCard hover={false} sx={{ p: { xs: 2, md: 3 } }}>
              <Typography variant="overline" sx={{ color: 'text.secondary' }}>Active sessions</Typography>
              <Stack spacing={1.25} sx={{ mt: 1.5 }} role="img" aria-label="Demo of three senders being started, stopped and finishing">
                {sessionRows.map((name, i) => {
                  const [status, sent, total] = sessionFrames[f][i];
                  const running = status === 'Sending';
                  return (
                    <Box key={name} sx={{ p: 1.5, borderRadius: 2, bgcolor: '#252526', border: '1px solid #333' }}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, fontWeight: 700, fontSize: 14 }}>
                        <Box component="span" sx={{ color: '#569cd6', fontSize: 10 }}>●</Box>{name}
                      </Box>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 0.75, fontFamily: mono, fontSize: 12 }}>
                        <Box component="span" sx={{ color: statusColor[status], transition: 'color .3s' }}>{status}</Box>
                        {total > 0 && <Box component="span" sx={{ color: 'text.secondary' }}>({sent}/{total})</Box>}
                        <Box sx={{ ml: 'auto', display: 'flex', gap: 0.75 }}>
                          {running ? btn('Stop', '#4d3d1f', '#d7ba7d') : btn('Start', '#2e7d32', '#fff')}
                          {btn('Try', '#3c3c3c', '#d4d4d4')}
                          {status === 'Failed' && btn('!', '#5a1d1d', '#f48771')}
                          {btn('✕', '#5a1d1d', '#f48771')}
                        </Box>
                      </Box>
                    </Box>
                  );
                })}
              </Stack>
            </GlassCard>
          </Reveal>
        </Grid>
      </Grid>
    </Container>
  );
}

const tagSamples = [
  { name: 'Ava', company: 'Northwind', word: 'harbor', file: 'Proposal_Northwind.pdf' },
  { name: 'Liam', company: 'Globex', word: 'meadow', file: 'Proposal_Globex.pdf' },
  { name: 'Mia', company: 'Initech', word: 'lantern', file: 'Proposal_Initech.pdf' },
];

function TagDemo() {
  const [i, setI] = useState(0);
  useEffect(() => {
    if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) return undefined;
    const id = setInterval(() => setI((v) => (v + 1) % tagSamples.length), 2600);
    return () => clearInterval(id);
  }, []);
  const s = tagSamples[i];
  const tag = (t) => <Box component="span" sx={{ color: neon.cyan, bgcolor: alpha(neon.cyan, 0.1), px: 0.5, borderRadius: 0.5 }}>{t}</Box>;
  const val = (t) => <Box component="span" key={t} sx={{ color: neon.green, fontWeight: 600, animation: 'pulseGlow .6s ease 1' }}>{t}</Box>;

  return (
    <Container maxWidth="lg" sx={{ py: { xs: 8, md: 12 } }}>
      <Grid container spacing={{ xs: 5, md: 8 }} sx={{ alignItems: 'center' }}>
        <Grid size={{ xs: 12, md: 5 }}>
          <SectionHeading align="left" eyebrow="Personalisation" title="Write once." highlight="Land as one-of-one." subtitle="Tags are resolved at send time in the subject, the body, the attachment and even the attachment's file name. Mix customer variables, random dynamic tags and real words from $dictionary." />
          <Stack direction="row" spacing={1} sx={{ flexWrap: 'wrap', rowGap: 1, mt: -3 }}>
            {['{name}', '{company}', '$dictionary', 'custom tags', 'AI-generated'].map((t) => (
              <Chip key={t} label={t} variant="outlined" sx={{ borderColor: alpha(neon.cyan, 0.3) }} />
            ))}
          </Stack>
        </Grid>
        <Grid size={{ xs: 12, md: 7 }}>
          <Reveal>
            <Grid container spacing={2}>
              <Grid size={{ xs: 12, sm: 6 }}>
                <GlassCard hover={false} sx={{ fontFamily: mono, fontSize: 13, lineHeight: 1.9 }}>
                  <Typography variant="overline" sx={{ color: 'text.secondary' }}>Template</Typography>
                  <Box>Subject: Quick idea for {tag('{company}')}</Box>
                  <Box sx={{ mt: 1.5 }}>Hi {tag('{name}')},</Box>
                  <Box>Code word: {tag('$dictionary')}</Box>
                  <Box sx={{ mt: 1.5, color: 'text.secondary' }}>📎 Proposal_{tag('{company}')}.pdf</Box>
                </GlassCard>
              </Grid>
              <Grid size={{ xs: 12, sm: 6 }}>
                <GlassCard hover={false} glow={neon.green} sx={{ fontFamily: mono, fontSize: 13, lineHeight: 1.9, borderColor: alpha(neon.green, 0.35), boxShadow: `0 0 60px -20px ${alpha(neon.green, 0.5)}` }}>
                  <Typography variant="overline" sx={{ color: neon.green }}>Recipient {i + 1} of 3</Typography>
                  <Box>Subject: Quick idea for {val(s.company)}</Box>
                  <Box sx={{ mt: 1.5 }}>Hi {val(s.name)},</Box>
                  <Box>Code word: {val(s.word)}</Box>
                  <Box sx={{ mt: 1.5, color: 'text.secondary' }}>📎 {val(s.file)}</Box>
                </GlassCard>
              </Grid>
            </Grid>
          </Reveal>
        </Grid>
      </Grid>
    </Container>
  );
}

function ApiSpotlight() {
  const flow = ['Create Google Cloud project', 'Enable the Gmail API', 'Configure OAuth consent', 'Create OAuth client & JSON', 'Sign in and grant send access'];
  const [step, setStep] = useState(0);
  useEffect(() => {
    if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) { setStep(flow.length); return undefined; }
    const id = setInterval(() => setStep((v) => (v > flow.length ? 0 : v + 1)), 1100);
    return () => clearInterval(id);
  }, [flow.length]);

  return (
    <Container maxWidth="lg" sx={{ py: { xs: 8, md: 12 } }}>
      <Grid container spacing={{ xs: 5, md: 8 }} direction={{ xs: 'column-reverse', md: 'row' }} sx={{ alignItems: 'center' }}>
        <Grid size={{ xs: 12, md: 6 }} sx={{ width: '100%' }}>
          <Reveal>
            <GlassCard hover={false} glow={neon.violet} sx={{ p: { xs: 3, md: 4 }, borderColor: alpha(neon.violet, 0.35) }}>
              <Typography variant="overline" sx={{ color: neon.violet }}>Gmail API · guided setup</Typography>
              <Stack spacing={1.5} sx={{ mt: 2 }}>
                {flow.map((f, i) => {
                  const done = i < step;
                  const active = i === step;
                  return (
                    <Box key={f} sx={{ display: 'flex', alignItems: 'center', gap: 1.5, p: 1.5, borderRadius: 2, border: `1px solid ${active ? alpha(neon.violet, 0.5) : neon.line}`, bgcolor: active ? alpha(neon.violet, 0.08) : 'transparent', transition: 'all .3s' }}>
                      <Box sx={{ width: 26, height: 26, borderRadius: '50%', display: 'grid', placeItems: 'center', fontFamily: mono, fontSize: 12, bgcolor: done ? neon.green : 'transparent', color: done ? '#04140c' : 'text.secondary', border: done ? 'none' : `1px solid ${neon.line}`, transition: 'all .3s' }}>
                        {done ? '✓' : i + 1}
                      </Box>
                      <Typography sx={{ color: done || active ? 'text.primary' : 'text.secondary', fontSize: 15 }}>{f}</Typography>
                      {active && <Box component="span" sx={{ ml: 'auto', fontFamily: mono, fontSize: 11, color: neon.violet, animation: 'pulseGlow 1s infinite' }}>RUNNING</Box>}
                    </Box>
                  );
                })}
              </Stack>
            </GlassCard>
          </Reveal>
        </Grid>
        <Grid size={{ xs: 12, md: 6 }}>
          <SectionHeading align="left" eyebrow="Gmail API mode" title="The Cloud Console," highlight="on autopilot." subtitle="Setting up the Gmail API usually means a dozen screens in Google Cloud. EzyMailer drives them for you — each Gmail account gets its own project, its own OAuth client and its own quota. Already have a credentials JSON? Just upload it." />
          <Button component={RouterLink} to="/features#gmail-api" endIcon={<ArrowForwardRounded />} sx={{ mt: -3, color: neon.violet }}>
            How Gmail API mode works
          </Button>
        </Grid>
      </Grid>
    </Container>
  );
}

function AttachmentOrbit() {
  const formats = [
    { t: 'PDF', c: '#FF5A5F' },
    { t: 'DOCX', c: '#4DA3FF' },
    { t: 'XLSX', c: neon.green },
    { t: 'PPTX', c: '#FFB547' },
    { t: 'PNG', c: neon.pink },
    { t: 'HTML', c: neon.cyan },
  ];
  return (
    <Container maxWidth="lg" sx={{ py: { xs: 8, md: 12 } }}>
      <Grid container spacing={{ xs: 5, md: 8 }} sx={{ alignItems: 'center' }}>
        <Grid size={{ xs: 12, md: 6 }}>
          <SectionHeading align="left" eyebrow="Attachment studio" title="Design one document." highlight="Ship a thousand." subtitle="Compose in a rich text editor or raw HTML, preview it live, and EzyMailer renders a personalised file for every recipient in the format you choose." />
        </Grid>
        <Grid size={{ xs: 12, md: 6 }}>
          <Reveal>
            <Box sx={{ position: 'relative', width: 'min(100%, 380px)', aspectRatio: '1', mx: 'auto' }}>
              <Box sx={{ position: 'absolute', inset: '6%', borderRadius: '50%', border: `1px dashed ${alpha(neon.cyan, 0.3)}` }} />
              <Box sx={{ position: 'absolute', inset: '18%', borderRadius: '50%', border: `1px solid ${neon.line}` }} />
              <Box sx={{ position: 'absolute', inset: '34%', borderRadius: '50%', display: 'grid', placeItems: 'center', background: `radial-gradient(circle, ${alpha(neon.cyan, 0.25)}, transparent 70%)` }}>
                <Box component="img" src="/logo.png" alt="" sx={{ width: '70%', filter: `drop-shadow(0 0 24px ${neon.cyan})` }} />
              </Box>
              <Box sx={{ position: 'absolute', inset: 0, animation: 'spinSlow 30s linear infinite' }}>
                {formats.map((f, i) => {
                  const a = (i / formats.length) * Math.PI * 2;
                  return (
                    <Box
                      key={f.t}
                      sx={{
                        position: 'absolute',
                        left: `${50 + 44 * Math.cos(a)}%`,
                        top: `${50 + 44 * Math.sin(a)}%`,
                        transform: 'translate(-50%, -50%)',
                      }}
                    >
                      <Box sx={{ animation: 'spinSlow 30s linear infinite reverse', px: 1.75, py: 1, borderRadius: 2, fontFamily: mono, fontWeight: 600, fontSize: 13, color: f.c, bgcolor: '#0A0F1E', border: `1px solid ${alpha(f.c, 0.5)}`, boxShadow: `0 0 24px -4px ${alpha(f.c, 0.6)}` }}>
                        .{f.t.toLowerCase()}
                      </Box>
                    </Box>
                  );
                })}
              </Box>
            </Box>
          </Reveal>
        </Grid>
      </Grid>
    </Container>
  );
}

function DownloadCTA() {
  return (
    <Container maxWidth="lg" sx={{ py: { xs: 8, md: 12 } }}>
      <Reveal>
        <Box
          sx={{
            position: 'relative',
            overflow: 'hidden',
            borderRadius: 6,
            p: { xs: 4, md: 8 },
            textAlign: 'center',
            border: `1px solid ${alpha(neon.cyan, 0.3)}`,
            background: `radial-gradient(ellipse at 50% 0%, ${alpha(neon.cyan, 0.18)}, transparent 60%), radial-gradient(ellipse at 100% 100%, ${alpha(neon.violet, 0.2)}, transparent 50%), #080D1A`,
          }}
        >
          <Stack direction="row" spacing={2} sx={{ justifyContent: 'center', mb: 3, color: 'text.secondary' }}>
            <Microsoft sx={{ fontSize: 34 }} />
            <Apple sx={{ fontSize: 34 }} />
          </Stack>
          <Typography variant="h2" sx={{ fontSize: { xs: '2rem', md: '3.2rem' } }}>
            Ready for <Box component="span" sx={gradientText}>lift-off?</Box>
          </Typography>
          <Typography color="text.secondary" sx={{ mt: 2, mb: 4.5, maxWidth: 560, mx: 'auto', fontSize: '1.1rem', lineHeight: 1.7 }}>
            Download EzyMailer for Windows or macOS and sign in with your account. Everything you need is in the box.
          </Typography>
          <DownloadButtons justify="center" />
          <Typography variant="body2" color="text.secondary" sx={{ mt: 3 }}>
            By downloading you agree to the{' '}
            <Box component={RouterLink} to="/terms" sx={{ color: neon.cyan }}>Terms</Box>,{' '}
            <Box component={RouterLink} to="/eula" sx={{ color: neon.cyan }}>EULA</Box> and{' '}
            <Box component={RouterLink} to="/acceptable-use" sx={{ color: neon.cyan }}>Acceptable Use Policy</Box>.
          </Typography>
        </Box>
      </Reveal>
    </Container>
  );
}

export default function Home() {
  return (
    <>
      <Hero />
      <Marquee />
      <Stats />
      <Engines />
      <HowItWorks />
      <FeatureBento />
      <SessionSpotlight />
      <TagDemo />
      <ApiSpotlight />
      <AttachmentOrbit />
      <DownloadCTA />
    </>
  );
}
