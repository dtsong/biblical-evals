/**
 * Auth.js (NextAuth.js v5) configuration.
 *
 * Uses Google OAuth with HS256-signed JWTs so the FastAPI backend
 * can verify tokens using the shared NEXTAUTH_SECRET.
 */

import NextAuth from "next-auth";
import Google from "next-auth/providers/google";
import * as jose from "jose";

const secret = process.env.NEXTAUTH_SECRET!;

export const { handlers, auth, signIn, signOut } = NextAuth({
  secret,
  trustHost: true,
  debug: process.env.NODE_ENV === "development",
  providers: [Google],

  session: {
    strategy: "jwt",
  },

  pages: {
    signIn: "/auth/login",
  },

  jwt: {
    async encode({ token }) {
      if (!token) return "";
      const secretKey = new TextEncoder().encode(secret);
      return await new jose.SignJWT(token as jose.JWTPayload)
        .setProtectedHeader({ alg: "HS256" })
        .setIssuedAt()
        .setExpirationTime("30d")
        .sign(secretKey);
    },
    async decode({ token }) {
      if (!token) return null;
      try {
        const secretKey = new TextEncoder().encode(secret);
        const { payload } = await jose.jwtVerify(token, secretKey, {
          algorithms: ["HS256"],
        });
        return payload;
      } catch {
        return null;
      }
    },
  },

  callbacks: {
    async jwt({ token, account, profile }) {
      if (account && profile) {
        token.sub = account.providerAccountId;
        token.email = profile.email;
        token.name = profile.name;
        token.picture = profile.picture as string | undefined;
      }
      return token;
    },
    async session({ session, token }) {
      if (session.user) {
        session.user.id = token.sub!;
        session.user.email = token.email as string;
        session.user.name = token.name as string;
        session.user.image = token.picture as string | undefined;
      }
      return session;
    },
  },
});
