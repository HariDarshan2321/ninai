import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";

import { SiteFooter } from "@/components/site-footer";
import { SiteHeader } from "@/components/site-header";

import "./globals.css";

const siteUrl = "https://ninai.io";

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title: {
    default: "Ninai — AI memory with boundaries",
    template: "%s — Ninai",
  },
  description:
    "Ninai remembers useful AI work across sessions, keeps the complete vault local, and releases only the context each assistant is allowed to recall.",
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
    title: "Your AI should remember the work. Not your whole life.",
    description:
      "Local-first AI memory with explicit permissions, provenance, and compact context packets.",
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
      "Your AI should remember the work—not your whole life.",
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
        "A local-first, permissioned memory layer for AI tools and MCP clients.",
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
