import { useMemo } from 'react';

// Best-effort guess of the visitor's desktop OS so we can lead with the right installer.
export default function useOS() {
  return useMemo(() => {
    if (typeof navigator === 'undefined') return 'unknown';
    const platform = (navigator.userAgentData?.platform || navigator.platform || navigator.userAgent || '').toLowerCase();
    if (platform.includes('mac')) return 'mac';
    if (platform.includes('win')) return 'windows';
    return 'unknown';
  }, []);
}
