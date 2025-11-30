import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";

// Professional Fonts
const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });
const jetbrains = JetBrains_Mono({ subsets: ["latin"], variable: "--font-mono" });

export const metadata: Metadata = {
  title: "MotoMind | AI First-Responder for Motorcyclists",
  description: "The first multimodal AI agent that sees, hears, and diagnoses motorcycle issues. Built with Gemini 2.0 and Google ADK.",
  keywords: ["AI", "Gemini", "MotoMind", "Mechanic", "Agent", "Hackathon"],
  openGraph: {
    title: "MotoMind AI",
    description: "Your pocket mechanic. Diagnoses engine sounds and visual damage instantly.",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.variable} ${jetbrains.variable} bg-[#0a0a0a] text-white antialiased`}>
        {children}
      </body>
    </html>
  );
}