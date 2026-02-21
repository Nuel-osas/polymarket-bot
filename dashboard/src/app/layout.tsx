"use client";

import { Inter, JetBrains_Mono } from "next/font/google";
import { SWRConfig } from "swr";
import "./globals.css";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

const jetbrains = JetBrains_Mono({
  variable: "--font-jetbrains",
  subsets: ["latin"],
});

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <head>
        <title>Polybot Dashboard</title>
        <meta name="description" content="Polybot trading bot monitoring dashboard" />
      </head>
      <body
        className={`${inter.variable} ${jetbrains.variable} font-sans antialiased`}
      >
        <SWRConfig
          value={{
            revalidateOnFocus: false,
            shouldRetryOnError: true,
            errorRetryCount: 3,
          }}
        >
          {children}
        </SWRConfig>
      </body>
    </html>
  );
}
