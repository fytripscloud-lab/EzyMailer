import { useEffect, useRef, useState } from 'react';
import Box from '@mui/material/Box';

// Fades and lifts its children in the first time they scroll into view.
export default function Reveal({ children, delay = 0, sx, ...rest }) {
  const ref = useRef(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const node = ref.current;
    if (!node) return undefined;
    const io = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setVisible(true);
          io.disconnect();
        }
      },
      { threshold: 0.12, rootMargin: '0px 0px -40px 0px' },
    );
    io.observe(node);
    return () => io.disconnect();
  }, []);

  return (
    <Box
      ref={ref}
      className={`reveal${visible ? ' is-visible' : ''}`}
      sx={{ transitionDelay: `${delay}ms`, ...sx }}
      {...rest}
    >
      {children}
    </Box>
  );
}
