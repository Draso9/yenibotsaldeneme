import { sendEmailVerification, type User } from "firebase/auth";
import { firebaseAuth } from "./firebase";

const IZFIN_VERIFICATION_RETURN_URL = "https://izfin-web.vercel.app/auth?verified=1";

export async function sendIzfinVerificationEmail(user: User): Promise<void> {
  const auth = firebaseAuth();
  auth.languageCode = "tr";
  await sendEmailVerification(user, {
    url: IZFIN_VERIFICATION_RETURN_URL,
    handleCodeInApp: false,
  });
}
