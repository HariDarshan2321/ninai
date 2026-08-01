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
    "Carry source-backed project decisions across Claude and Codex with explicit permissions and immediate revocation.",
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
    title: "Ninai AI memory for Claude Code and Codex",
    description:
      "Remember project decisions once, recall them with sources, and revoke access at any time.",
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
    title: "Ninai AI memory for Claude Code and Codex",
    description:
      "Shared, source-backed project memory for Claude and Codex.",
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
      sameAs: ["https://github.com/HariDarshan2321/ninai"],
    },
    {
      "@type": "WebSite",
      "@id": `${siteUrl}/#website`,
      url: `${siteUrl}/`,
      name: "Ninai",
      alternateName: "Ninai AI Memory",
      publisher: { "@id": `${siteUrl}/#organization` },
      inLanguage: "en",
    },
    {
      "@type": "SoftwareApplication",
      "@id": `${siteUrl}/#software`,
      name: "Ninai",
      applicationCategory: "DeveloperApplication",
      operatingSystem: "macOS",
      url: `${siteUrl}/`,
      description:
        "Permissioned, source-backed AI memory for Claude Code and Codex.",
      softwareVersion: "0.1",
      downloadUrl: `${siteUrl}/download/install-ninai-macos.sh`,
      softwareHelp: `${siteUrl}/install/`,
      codeRepository: "https://github.com/HariDarshan2321/ninai",
      isPartOf: { "@id": `${siteUrl}/#website` },
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
