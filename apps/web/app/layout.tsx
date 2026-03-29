import type { Metadata } from "next";
import type { ReactNode } from "react";
import { Space_Grotesk, Newsreader } from "next/font/google";

import "./globals.css";

const spaceGrotesk = Space_Grotesk({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-ui",
  display: "swap",
});

const newsreader = Newsreader({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  style: ["normal", "italic"],
  variable: "--font-narrative",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Mimir",
  description: "Frontend Stage 0 harness for the Mimir research workspace.",
};

type RootLayoutProps = {
  children: ReactNode;
};

export default function RootLayout({ children }: RootLayoutProps) {
  return (
    <html
      lang="zh-CN"
      className={`${spaceGrotesk.variable} ${newsreader.variable}`}
    >
      <body className="grain-overlay">{children}</body>
    </html>
  );
}
