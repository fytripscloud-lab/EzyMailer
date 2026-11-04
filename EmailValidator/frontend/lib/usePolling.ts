import { useEffect, useRef } from "react";

/**
 * Repeatedly calls `fn` every `intervalMs` while `active` is true, starting
 * immediately. Guards against overlapping calls and cleans up on unmount or
 * when `active` flips to false.
 */
export function usePolling(fn: () => Promise<void>, intervalMs: number, active: boolean): void {
  const fnRef = useRef(fn);

  useEffect(() => {
    fnRef.current = fn;
  }, [fn]);

  useEffect(() => {
    if (!active) return;

    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | null = null;

    const tick = async () => {
      if (cancelled) return;
      try {
        await fnRef.current();
      } finally {
        if (!cancelled) {
          timer = setTimeout(tick, intervalMs);
        }
      }
    };

    tick();

    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [active, intervalMs]);
}
