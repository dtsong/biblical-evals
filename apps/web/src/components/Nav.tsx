"use client";

import React from "react";
import { useSession, signIn, signOut } from "next-auth/react";
import Link from "next/link";
import { BookOpen, LogIn, LogOut } from "lucide-react";

import { accessApi } from "@/lib/api";

export function Nav() {
  const { data: session } = useSession();
  const [isAdmin, setIsAdmin] = React.useState(false);

  React.useEffect(() => {
    if (!session) {
      setIsAdmin(false);
      return;
    }

    accessApi
      .me()
      .then((me) => setIsAdmin(me.is_admin))
      .catch(() => setIsAdmin(false));
  }, [session]);

  return (
    <header className="border-b border-border/60 bg-card/80 backdrop-blur-sm sticky top-0 z-50">
      <div className="container mx-auto px-4 max-w-6xl flex items-center justify-between h-14">
        <Link
          href="/"
          className="flex items-center gap-2.5 group"
        >
          <BookOpen className="h-5 w-5 text-primary transition-transform group-hover:scale-110" />
          <span
            className="text-lg font-semibold tracking-tight"
            style={{ fontFamily: "var(--font-display)" }}
          >
            Biblical Evals
          </span>
        </Link>

        <nav className="flex items-center gap-6">
          {session && (
            <>
              <Link
                href="/evaluations"
                className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
              >
                Evaluations
              </Link>
              {isAdmin && (
                <Link
                  href="/admin/access"
                  className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
                >
                  Admin
                </Link>
              )}
            </>
          )}

          {session ? (
            <button
              onClick={() => signOut()}
              className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              <LogOut className="h-3.5 w-3.5" />
              Sign Out
            </button>
          ) : (
            <button
              onClick={() => signIn("google")}
              className="flex items-center gap-1.5 text-sm font-medium text-primary hover:text-primary/80 transition-colors"
            >
              <LogIn className="h-3.5 w-3.5" />
              Sign In
            </button>
          )}
        </nav>
      </div>
    </header>
  );
}
