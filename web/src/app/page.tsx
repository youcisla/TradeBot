import { redirect } from "next/navigation";

// Always send the root URL to login. Authenticated users will be redirected
// to /dashboard by the login page once their JWT cookie is detected.
export default function Home() {
  redirect("/login");
}
