import Chip from "@mui/material/Chip";
import type { ChipProps } from "@mui/material/Chip";

const COLOR_MAP: Record<string, ChipProps["color"]> = {
  valid: "success",
  accepted: "success",
  found: "success",
  yes_good: "success",
  invalid: "error",
  rejected: "error",
  not_found: "error",
  risky: "warning",
  yes_risky: "warning",
  unknown: "default",
  no: "default",
};

function normalize(label: string): string {
  return label.toLowerCase().replace(/\s+/g, "_");
}

interface StatusBadgeProps {
  label: string;
  tone?: "good" | "bad" | "risky" | "neutral";
}

export default function StatusBadge({ label, tone }: StatusBadgeProps) {
  let color: ChipProps["color"] = "default";
  if (tone === "good") color = "success";
  else if (tone === "bad") color = "error";
  else if (tone === "risky") color = "warning";
  else if (tone === "neutral") color = "default";
  else color = COLOR_MAP[normalize(label)] ?? "default";

  return <Chip label={label} color={color} size="small" variant={color === "default" ? "outlined" : "filled"} />;
}
