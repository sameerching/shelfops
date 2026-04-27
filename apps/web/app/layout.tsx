import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ShelfOps",
  description: "ShelfOps quick-commerce recovery platform"
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
