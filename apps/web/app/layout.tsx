import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ASICify · Compiler for AI silicon",
  description:
    "Open-source compiler that turns trained PyTorch models into synthesizable Verilog, with area and cost estimates across eleven hardware targets.",
  openGraph: {
    title: "ASICify",
    description: "Open-source compiler. PyTorch to synthesizable Verilog.",
    siteName: "ASICify",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "ASICify",
    description: "Open-source compiler. PyTorch to synthesizable Verilog.",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <head>
        <link
          rel="preconnect"
          href="https://rsms.me/"
          crossOrigin="anonymous"
        />
        <link
          rel="stylesheet"
          href="https://rsms.me/inter/inter.css"
        />
      </head>
      <body>{children}</body>
    </html>
  );
}
