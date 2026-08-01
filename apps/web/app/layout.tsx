import type { Metadata } from "next";
import { Archivo, JetBrains_Mono } from "next/font/google";
import "./globals.css";

const archivo = Archivo({
  subsets: ["latin"],
  axes: ["wdth"],
  variable: "--font-archivo",
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-jetbrains",
  display: "swap",
});

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
    <html lang="en" className={`${archivo.variable} ${jetbrainsMono.variable}`}>
      <body>{children}</body>
    </html>
  );
}
