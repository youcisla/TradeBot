import { withAuth } from "next-auth/middleware";

// Protect all /dashboard routes at the Edge — JWT token is validated here
// without a database call, making auth checks sub-millisecond.
// This replaces the getServerSession() call that was in dashboard/layout.tsx.
export default withAuth({
  pages: { signIn: "/login" },
});

export const config = {
  matcher: ["/dashboard/:path*"],
};
