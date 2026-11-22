import type { Metadata } from "next";

export const siteUrl = "https://ninai.io";

type PageMetadata = {
  path: `/${string}`;
  title: string;
  description: string;
  index?: boolean;
};

export function pageMetadata({ path, title, description, index = true }: PageMetadata): Metadata {
  const fullTitle = `${title} - Ninai`;
  const image = {
    url: "/assets/og-image.png",
    width: 1200,
    height: 630,
    alt: "Ninai local AI memory with project permissions",
  };

  return {
    title: { absolute: fullTitle },
    description,
    alternates: { canonical: path },
    openGraph: {
      type: "website",
      url: path,
      siteName: "Ninai",
      title: fullTitle,
      description,
      images: [image],
    },
    twitter: {
      card: "summary_large_image",
      title: fullTitle,
      description,
      images: [image],
    },
    ...(index ? {} : { robots: { index: false, follow: true } }),
  };
}
