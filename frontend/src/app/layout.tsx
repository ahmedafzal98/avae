import type { Metadata } from "next";
import { Inter, JetBrains_Mono, Noto_Sans_Arabic } from "next/font/google";
import { ClerkProvider } from "@clerk/nextjs";
import { Toaster } from "sonner";
import { Providers } from "@/components/providers";
import "./globals.css";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  variable: "--font-jetbrains-mono",
  subsets: ["latin"],
  display: "swap",
});

const notoSansArabic = Noto_Sans_Arabic({
  variable: "--font-arabic",
  subsets: ["arabic"],
  display: "swap",
  weight: ["400", "500", "600", "700"],
});

export const metadata: Metadata = {
  title: "AVAE — Agentic Verification and Audit Engine",
  description: "Enterprise compliance and audit platform for UK Financial Services",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="light" suppressHydrationWarning>
      <body
        className={`${inter.variable} ${jetbrainsMono.variable} ${notoSansArabic.variable} font-sans antialiased`}
      >
        <ClerkProvider>
          <Providers>{children}</Providers>
          <Toaster position="top-right" richColors closeButton />
        </ClerkProvider>
      </body>
    </html>
  );
}
