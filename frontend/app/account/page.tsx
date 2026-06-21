"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function AccountRedirectPage() {
  const router = useRouter();

  useEffect(() => {
    router.replace("/login");
  }, [router]);

  return (
    <section className="card stack">
      <span className="pill">Conta</span>
      <h1>Redirecionando para login...</h1>
    </section>
  );
}
