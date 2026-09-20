import { readFileSync } from "node:fs";
const css = readFileSync(new URL("../src/app/tokens.css", import.meta.url), "utf8");
const colors = Object.fromEntries([...css.matchAll(/--color-([\w-]+):\s*(#[a-f0-9]{6})/g)].map((m) => [m[1], m[2]]));
function luminance(hex) {
  const values = hex.slice(1).match(/../g).map((v) => parseInt(v, 16) / 255).map((v) => v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4);
  return values[0] * 0.2126 + values[1] * 0.7152 + values[2] * 0.0722;
}
const pairs = [["ink", "canvas", 4.5], ["ink-muted", "canvas", 4.5], ["on-brand", "brand", 4.5], ["on-brand", "brand-hover", 4.5], ["danger", "danger-soft", 4.5], ["success", "success-soft", 4.5], ["warning", "warning-soft", 4.5], ["input-border", "surface", 3], ["focus", "canvas", 3]];
for (const [foreground, background, minimum] of pairs) {
  const values = [luminance(colors[foreground]), luminance(colors[background])].sort((a, b) => b - a);
  const ratio = (values[0] + 0.05) / (values[1] + 0.05);
  console.log(`${foreground}/${background}: ${ratio.toFixed(2)}:1`);
  if (ratio < minimum) process.exitCode = 1;
}
