import NextAuth from "next-auth";
import CredentialsProvider from "next-auth/providers/credentials";
import bcrypt from "bcryptjs";
import { getUserByUsername } from "@/lib/db";

export const authOptions = {
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

        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const creds = credentials as any;
        const username = creds.username.trim().toLowerCase();
        const password = creds.password;

        const user = await getUserByUsername(username);
        if (!user || !user.password_hash) return null;

        const valid = await bcrypt.compare(password, user.password_hash);
        if (!valid) return null;

        return { id: String(user.id), name: user.username };
      },
    }),
  ],
  pages: { signIn: "/login" },
  session: { strategy: "jwt" as const, maxAge: 7 * 24 * 60 * 60 },
  callbacks: {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    async jwt({ token, user }: any) {
      if (user) {
        token.userId = Number(user.id);
        token.username = user.name;
      }
      return token;
    },
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    async session({ session, token }: any) {
      if (session.user) {
        session.user.id = token.userId;
        session.user.username = token.username;
      }
      return session;
    },
  },
  secret: process.env.NEXTAUTH_SECRET,
};

export const auth = NextAuth(authOptions);
