import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ASICify · An open compiler from PyTorch to silicon",
  description:
    "ASICify takes a trained PyTorch model and emits synthesizable Verilog, a Cocotb testbench, and area-and-cost estimates across eleven hardware targets. MIT licensed. You run it. You keep the RTL.",
  openGraph: {
    title: "ASICify",
    description:
      "An open compiler from PyTorch to silicon. You run it. You keep the RTL.",
    siteName: "ASICify",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "ASICify",
    description:
      "An open compiler from PyTorch to silicon. You run it. You keep the RTL.",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://rsms.me/" crossOrigin="anonymous" />
        <link rel="stylesheet" href="https://rsms.me/inter/inter.css" />
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link
          rel="preconnect"
          href="https://fonts.gstatic.com"
          crossOrigin="anonymous"
        />
        <link
          rel="stylesheet"
          href="https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=JetBrains+Mono:wght@400;500;600&display=swap"
        />
      </head>
      <body>{children}</body>
    </html>
  );
}
