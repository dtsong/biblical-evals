"use client";

import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useSession } from "next-auth/react";

import { accessApi, isAccessPendingError } from "@/lib/api";

const EXEMPT_PATHS = ["/", "/auth/login", "/api/auth", "/access/pending"];

function isExemptPath(pathname: string): boolean {
  return EXEMPT_PATHS.some((path) => pathname === path || pathname.startsWith(path + "/"));
}

export function AccessGate() {
  const { data: session, status } = useSession();
  const pathname = usePathname();
  const router = useRouter();

  useEffect(() => {
    if (status !== "authenticated" || !session?.user) return;

    accessApi
      .me()
      .then((me) => {
        if (!me.is_admin && pathname.startsWith("/admin")) {
          router.replace("/evaluations");
          return;
        }

        const approved = me.is_admin || me.access_status === "approved";
        if (!approved && pathname !== "/access/pending" && !isExemptPath(pathname)) {
          router.replace("/access/pending");
          return;
        }

        if (approved && pathname === "/access/pending") {
          router.replace("/evaluations");
        }
      })
      .catch((err) => {
        if (isAccessPendingError(err) && pathname !== "/access/pending") {
          router.replace("/access/pending");
        }
      });
  }, [pathname, router, session, status]);

  return null;
}
