import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "DocuMindAI — Intelligent Document Workspace",
  description:
    "Search, understand, and chat with your documents using AI.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
