"use client";

import { useEffect, useRef } from "react";
import Box from "@mui/material/Box";
import { keyframes } from "@mui/material/styles";

import type { ActivityEntry } from "@/lib/types";

const blink = keyframes`
  0%, 49% { opacity: 1; }
  50%, 100% { opacity: 0; }
`;

const MONO_FONT = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace";

const STATUS_COLOR: Record<string, string> = {
  valid: "#3fb950",
  invalid: "#f85149",
  risky: "#d29922",
  unknown: "#8b949e",
};

interface TerminalLogProps {
  lines: ActivityEntry[];
  active: boolean;
  total: number;
}

export default function TerminalLog({ lines, active, total }: TerminalLogProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [lines]);

  return (
    <Box sx={{ mt: 3, bgcolor: "#0b0f14", borderRadius: 2, border: "1px solid #1f2630", overflow: "hidden" }}>
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          gap: 0.75,
          px: 1.5,
          py: 1,
          bgcolor: "#141a21",
          borderBottom: "1px solid #1f2630",
        }}
      >
        <Box sx={{ width: 10, height: 10, borderRadius: "50%", bgcolor: "#ff5f56" }} />
        <Box sx={{ width: 10, height: 10, borderRadius: "50%", bgcolor: "#ffbd2e" }} />
        <Box sx={{ width: 10, height: 10, borderRadius: "50%", bgcolor: "#27c93f" }} />
        <Box component="span" sx={{ ml: 1, color: "#8b949e", fontFamily: MONO_FONT, fontSize: 12 }}>
          validator — live
        </Box>
      </Box>

      <Box
        ref={scrollRef}
        sx={{
          height: 220,
          overflowY: "auto",
          p: 1.5,
          fontFamily: MONO_FONT,
          fontSize: 13,
          lineHeight: 1.7,
        }}
      >
        <Box sx={{ color: "#8b949e", mb: 0.5 }}>
          $ validating {total} email{total === 1 ? "" : "s"}…
        </Box>

        {lines.length === 0 && <Box sx={{ color: "#8b949e" }}>waiting for the first results…</Box>}

        {lines.map((line, i) => (
          <Box key={`${line.email}-${i}`} sx={{ whiteSpace: "pre-wrap", wordBreak: "break-all" }}>
            <Box component="span" sx={{ color: "#8b949e" }}>
              [{line.timestamp}]{" "}
            </Box>
            <Box component="span" sx={{ color: "#c9d1d9" }}>
              checking {line.email} …{" "}
            </Box>
            <Box component="span" sx={{ color: STATUS_COLOR[line.status] ?? "#c9d1d9", fontWeight: 700 }}>
              {line.status.toUpperCase()}
            </Box>
          </Box>
        ))}

        {active && (
          <Box
            component="span"
            sx={{
              display: "inline-block",
              width: 8,
              height: 14,
              bgcolor: "#58a6ff",
              verticalAlign: "text-bottom",
              animation: `${blink} 1s step-end infinite`,
            }}
          />
        )}
      </Box>
    </Box>
  );
}
