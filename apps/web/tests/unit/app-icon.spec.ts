import { readFileSync } from "node:fs";
import path from "node:path";

import { expect, test } from "vitest";

test("provides the branded svg favicon at the app router icon path", () => {
  const iconPath = path.resolve(process.cwd(), "app/icon.svg");
  const svg = readFileSync(iconPath, "utf8").trim();

  expect(svg).toBe(`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" width="256" height="256">
  <rect width="256" height="256" fill="#000000"/>
  <g fill="#FFFFFF">
    <rect x="20" y="52" width="24" height="24"/>
    <rect x="212" y="52" width="24" height="24"/>
    <rect x="20" y="84" width="24" height="24"/>
    <rect x="52" y="84" width="24" height="24"/>
    <rect x="180" y="84" width="24" height="24"/>
    <rect x="212" y="84" width="24" height="24"/>
    <rect x="20" y="116" width="24" height="24"/>
    <rect x="84" y="116" width="24" height="24"/>
    <rect x="148" y="116" width="24" height="24"/>
    <rect x="212" y="116" width="24" height="24"/>
    <rect x="20" y="148" width="24" height="24"/>
    <rect x="116" y="148" width="24" height="24"/>
    <rect x="212" y="148" width="24" height="24"/>
    <rect x="20" y="180" width="24" height="24"/>
    <rect x="212" y="180" width="24" height="24"/>
  </g>
</svg>`);
});
