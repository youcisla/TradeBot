import type { NextAuthOptions } from "next-auth";
import CredentialsProvider from "next-auth/providers/credentials";
import bcrypt from "bcryptjs";
import { getUserByUsername } from "@/lib/db";

export const authOptions: NextAuthOptions = {
  providers: [
    CredentialsProvider({
      name: "Credentials",
      credentials: {
        username: { label: "Username", type: "text" },
        password: { label: "Password", type: "password" },
      },
      async authorize(credentials) {
        if (!process.env.NEXTAUTH_SECRET) {
          throw new Error(
            "NEXTAUTH_SECRET is not set. Add it to your Vercel environment variables. " +
            "Generate one with: openssl rand -base64 32"
          );
        }

        if (!credentials?.username || !credentials?.password) return null;

        const username = credentials.username.trim().toLowerCase();
        const password = credentials.password;

        // Normal login — verify against DB
        // To create the first user run: python scripts/reset_dashboard_user.py
        const user = await getUserByUsername(username);
        if (!user || !user.password_hash) return null;

        const valid = await bcrypt.compare(password, user.password_hash);
        if (!valid) return null;

        return { id: String(user.id), name: user.username };
      },
    }),
  ],
  pages: { signIn: "/login" },
  session: { strategy: "jwt", maxAge: 7 * 24 * 60 * 60 },
  callbacks: {
    async jwt({ token, user }) {
      if (user) {
        token.userId = Number(user.id);
        token.username = user.name;
      }
      return token;
    },
    async session({ session, token }) {
      if (session.user) {
        (session.user as Record<string, unknown>).id = token.userId;
        (session.user as Record<string, unknown>).username = token.username;
      }
      return session;
    },
  },
  secret: process.env.NEXTAUTH_SECRET,
};
