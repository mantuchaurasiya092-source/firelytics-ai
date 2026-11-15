import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "FIRELYTICS AI | Combustion research intelligence",
  description: "Evidence-first navigation across NASA Physical Sciences Informatics microgravity combustion investigations.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en" data-theme="dark" suppressHydrationWarning><body>{children}</body></html>;
}
