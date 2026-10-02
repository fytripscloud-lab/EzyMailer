import Container from '@mui/material/Container';
import Box from '@mui/material/Box';
import SectionHeading from './SectionHeading';

// Shared top-of-page header for inner pages.
export default function PageHero(props) {
  return (
    <Box sx={{ pt: { xs: 8, md: 12 }, pb: { xs: 2, md: 4 } }}>
      <Container maxWidth="lg">
        <SectionHeading as="h1" {...props} />
      </Container>
    </Box>
  );
}
