import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ASICify — The compiler for AI silicon",
  description:
    "ASICify compiles trained PyTorch models into hardware-ready specifications. Synthesizable Verilog, area estimates across foundry nodes, FPGA reference implementations.",
  metadataBase: new URL("https://asicify.com"),
  openGraph: {
    title: "ASICify",
    description: "From PyTorch to silicon in minutes.",
    url: "https://asicify.com",
    siteName: "ASICify",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "ASICify",
    description: "From PyTorch to silicon in minutes.",
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
