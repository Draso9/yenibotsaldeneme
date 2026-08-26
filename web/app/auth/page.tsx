import { AuthPage } from "../../components/auth-page";
import { Suspense } from "react";

export default function AuthRoute() {
  return <Suspense fallback={<main className="auth-page" />}><AuthPage /></Suspense>;
}

