import Container from '@mui/material/Container';
import Accordion from '@mui/material/Accordion';
import AccordionSummary from '@mui/material/AccordionSummary';
import AccordionDetails from '@mui/material/AccordionDetails';
import Typography from '@mui/material/Typography';
import Stack from '@mui/material/Stack';
import Button from '@mui/material/Button';
import Box from '@mui/material/Box';
import AddRounded from '@mui/icons-material/AddRounded';
import { Link as RouterLink } from 'react-router-dom';
import PageHero from '../components/PageHero';
import Reveal from '../components/Reveal';
import { faqs } from '../data/faq';
import { neon } from '../theme';

export default function FAQ() {
  return (
    <>
      <PageHero eyebrow="FAQ" title="Questions," highlight="answered." subtitle="The things people ask most before and after installing EzyMailer." />
      <Container maxWidth="md">
        <Stack spacing={1.5}>
          {faqs.map((f, i) => (
            <Reveal key={f.q} delay={i * 40}>
              <Accordion disableGutters>
                <AccordionSummary
                  expandIcon={<AddRounded sx={{ color: neon.cyan }} />}
                  sx={{ px: 3, py: 1, '& .MuiAccordionSummary-expandIconWrapper.Mui-expanded': { transform: 'rotate(45deg)' } }}
                >
                  <Typography sx={{ fontWeight: 600, fontSize: '1.05rem' }}>{f.q}</Typography>
                </AccordionSummary>
                <AccordionDetails sx={{ px: 3, pb: 3 }}>
                  <Typography color="text.secondary" sx={{ lineHeight: 1.75 }}>{f.a}</Typography>
                </AccordionDetails>
              </Accordion>
            </Reveal>
          ))}
        </Stack>
        <Box sx={{ textAlign: 'center', mt: 6 }}>
          <Typography color="text.secondary" sx={{ mb: 2 }}>Still curious?</Typography>
          <Button component={RouterLink} to="/contact" variant="outlined">Ask us anything</Button>
        </Box>
      </Container>
    </>
  );
}
