import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";

import { SiteFooter } from "@/components/site-footer";
import { SiteHeader } from "@/components/site-header";

import "./globals.css";

const siteUrl = "https://ninai.io";

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title: {
    default: "Ninai — shared AI memory with boundaries",
    template: "%s — Ninai",
  },
  description:
    "Permissioned, source-backed memory for AI tools, with an open-source local engine and hosted cross-provider beta in development.",
  applicationName: "Ninai",
  alternates: { canonical: "/" },
  manifest: "/site.webmanifest",
  icons: {
    icon: "/assets/ninai-app-icon.svg",
    apple: "/assets/ninai-app-icon.svg",
  },
  openGraph: {
    type: "website",
    url: siteUrl,
    siteName: "Ninai",
    title: "One memory for OpenAI and Claude — in development",
    description:
      "Explore Ninai's available local engine and hosted cross-provider beta in development.",
    images: [
      {
        url: "/assets/og-image.png",
        width: 1200,
        height: 630,
        alt: "Ninai — AI memory with boundaries",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "Ninai — AI memory with boundaries",
    description:
      "Permissioned AI memory: local today, hosted cross-provider beta in development.",
    images: ["/assets/og-image.png"],
  },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      "max-image-preview": "large",
      "max-snippet": -1,
      "max-video-preview": -1,
    },
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#10120f",
  colorScheme: "light dark",
};

const organizationSchema = {
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "Organization",
      "@id": `${siteUrl}/#organization`,
      name: "Ninai",
      url: `${siteUrl}/`,
      logo: `${siteUrl}/assets/ninai-wordmark.svg`,
      email: "hello@ninai.io",
    },
    {
      "@type": "WebSite",
      "@id": `${siteUrl}/#website`,
      url: `${siteUrl}/`,
      name: "Ninai",
      publisher: { "@id": `${siteUrl}/#organization` },
      inLanguage: "en",
    },
    {
      "@type": "SoftwareApplication",
      name: "Ninai",
      applicationCategory: "DeveloperApplication",
      operatingSystem: "macOS, Linux, Windows",
      url: `${siteUrl}/`,
      description:
        "A permissioned memory layer for AI tools, with an available local engine and hosted mode in development.",
      softwareVersion: "0.1",
      offers: { "@type": "Offer", price: "0", priceCurrency: "EUR" },
      publisher: { "@id": `${siteUrl}/#organization` },
    },
  ],
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en" data-scroll-behavior="smooth">
      <body>
        <a className="skip-link" href="#main-content">
          Skip to content
        </a>
        <SiteHeader />
        {children}
        <SiteFooter />
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(organizationSchema) }}
        />
      </body>
    </html>
  );
}
