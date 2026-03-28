import type { NextAuthOptions } from "next-auth";
import CredentialsProvider from "next-auth/providers/credentials";
import bcrypt from "bcryptjs";
import { getUserByUsername, getUserCount, createUser } from "@/lib/db";

if (!process.env.NEXTAUTH_SECRET) {
  throw new Error(
    "NEXTAUTH_SECRET is not set. Set this environment variable to a random 32+ character string. " +
    "Run: openssl rand -base64 32"
  );
}

export const authOptions: NextAuthOptions = {
  providers: [
    CredentialsProvider({
      name: "Credentials",
      credentials: {
        username: { label: "Username", type: "text" },
        password: { label: "Password", type: "password" },
      },
      async authorize(credentials) {
        if (!credentials?.username || !credentials?.password) return null;

        const username = credentials.username.trim().toLowerCase();
        const password = credentials.password;

        // Auto-create first user if no users exist yet (initial setup).
        // WARNING: any caller can claim admin on a fresh/wiped DB.
        // Use scripts/reset_dashboard_user.py to pre-create credentials instead.
        const count = await getUserCount();
        if (count === 0) {
          console.warn(
            `[auth] WARNING: No users exist — auto-creating first user '${username}'. ` +
            "Run scripts/reset_dashboard_user.py to set credentials before exposing the dashboard."
          );
          const hash = await bcrypt.hash(password, 12);
          const id = await createUser(username, hash);
          return { id: String(id), name: username };
        }

        // Normal login — verify against DB
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
