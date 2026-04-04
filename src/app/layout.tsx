import type { Metadata } from "next";
import { Space_Grotesk, Playfair_Display } from "next/font/google";
import "./globals.css";

const spaceGrotesk = Space_Grotesk({
  variable: "--font-space-grotesk",
  subsets: ["latin"],
});

const playfair = Playfair_Display({
  variable: "--font-playfair",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Hexamind — ARIA Intelligence Pipeline",
  description: "Multi-agent adversarial reasoning visualised as a live node graph.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${spaceGrotesk.variable} ${playfair.variable} h-full antialiased dark`}
    >
      <body className="min-h-screen overflow-x-hidden bg-[#0a0b0f] text-foreground selection:bg-indigo-charcoal selection:text-white">
        {children}
      </body>
    </html>
  );
}
