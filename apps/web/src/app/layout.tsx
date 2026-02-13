import type { Metadata } from "next";
import "./globals.css";
import { Providers } from "./providers";
import { Nav } from "@/components/Nav";

export const metadata: Metadata = {
  title: "Biblical Evals",
  description:
    "Framework for evaluating LLM responses to biblical and theological questions",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen parchment-bg">
        <Providers>
          <Nav />
          <main className="container mx-auto px-4 py-8 max-w-6xl">
            {children}
          </main>
        </Providers>
      </body>
    </html>
  );
}
