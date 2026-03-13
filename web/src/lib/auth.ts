import type { NextAuthOptions } from "next-auth";
import CredentialsProvider from "next-auth/providers/credentials";

if (!process.env.NEXTAUTH_SECRET) {
  console.warn("WARNING: NEXTAUTH_SECRET is not set!");
}

export const authOptions: NextAuthOptions = {
  providers: [
    CredentialsProvider({
      name: "Password",
      credentials: {
        password: { label: "Password", type: "password" },
      },
      async authorize(credentials) {
        const pwd = process.env.DASHBOARD_PASSWORD;
        if (!pwd) {
          console.error("DASHBOARD_PASSWORD env var is not set");
          return null;
        }
        if (credentials?.password === pwd) {
          return { id: "1", name: "Admin" };
        }
        return null;
      },
    }),
  ],
  pages: { signIn: "/login" },
  session: { strategy: "jwt", maxAge: 7 * 24 * 60 * 60 },
  secret: process.env.NEXTAUTH_SECRET,
};
