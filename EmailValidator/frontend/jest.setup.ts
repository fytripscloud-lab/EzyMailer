import { TextDecoder, TextEncoder } from "util";

import "@testing-library/jest-dom";

if (typeof globalThis.TextEncoder === "undefined") {
  globalThis.TextEncoder = TextEncoder as unknown as typeof globalThis.TextEncoder;
  globalThis.TextDecoder = TextDecoder as unknown as typeof globalThis.TextDecoder;
}

// jsdom doesn't implement structuredClone, but @mui/x-charts' internal
// gesture handling calls it as soon as a chart (PieChart/BarChart) mounts.
if (typeof globalThis.structuredClone === "undefined") {
  globalThis.structuredClone = (value: unknown) => JSON.parse(JSON.stringify(value));
}
