import type { Metadata } from "next";
import Link from "next/link";
import { AdminSessionControls } from "./components/AdminSessionControls";
import { AppNav } from "./components/AppNav";
import { SessionProvider } from "./components/SessionProvider";
import { UserSessionControls } from "./components/UserSessionControls";
import "./styles.css";

export const metadata: Metadata = {
  title: "LinguaFlow AI",
  description: "Language learning with conversational AI, RAG, voice, analytics and auditability.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="pt-BR">
      <body>
        <SessionProvider>
          <header className="topbar">
            <Link href="/" className="brand"><span className="brand-mark">LF</span> LinguaFlow AI</Link>
            <AppNav />
            <UserSessionControls />
            <AdminSessionControls />
          </header>
          <main>{children}</main>
        </SessionProvider>
      </body>
    </html>
  );
}
