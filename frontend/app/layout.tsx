import type { Metadata } from "next";
import Link from "next/link";
import "./styles.css";

export const metadata: Metadata = {
  title: "LinguaFlow AI",
  description: "Language learning with conversational AI, RAG, voice, analytics and auditability.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="pt-BR">
      <body>
        <header className="topbar">
          <Link href="/" className="brand">LinguaFlow AI</Link>
          <nav>
            <Link href="/chat">Chat</Link>
            <Link href="/dashboard">Dashboard</Link>
            <Link href="/admin">Admin RAG</Link>
          </nav>
        </header>
        <main>{children}</main>
      </body>
    </html>
  );
}
