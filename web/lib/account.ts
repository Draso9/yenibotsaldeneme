import { izfinApiFetch, izfinPublicApiFetch } from "./api";

export type ProfileResponse = {
  uid: string;
  email: string;
  profile: Record<string, unknown>;
};

export type LegalConsentResponse = {
  terms_version: string;
  privacy_version: string;
  accepted: boolean;
};

export type LegalDocumentResponse = {
  version: string;
  markdown: string;
  warning: string | null;
  info: string | null;
};

export type AccountExportResponse = {
  export_schema: string;
  exported_at: string;
  app_release: string;
  user_uid: string;
  user_email: string;
  collections: Record<string, Array<Record<string, unknown>>>;
};

export type AccountDeleteResponse = {
  deleted: boolean;
  deleted_documents: number;
};

export function accountDeletePath(): "/api/v1/account" { return "/api/v1/account"; }
export function accountExportPath(): "/api/v1/account/export" { return "/api/v1/account/export"; }
export function legalTermsPath(): "/api/v1/legal/terms" { return "/api/v1/legal/terms"; }
export function legalPrivacyPath(): "/api/v1/legal/privacy" { return "/api/v1/legal/privacy"; }

export function fetchProfile(idToken: string): Promise<ProfileResponse> {
  return izfinApiFetch<ProfileResponse>("/api/v1/profile", idToken);
}

export function bootstrapAccount(idToken: string): Promise<ProfileResponse> {
  return izfinApiFetch<ProfileResponse>("/api/v1/account/bootstrap", idToken, { method: "POST" });
}

export function fetchLegalConsent(idToken: string): Promise<LegalConsentResponse> {
  return izfinApiFetch<LegalConsentResponse>("/api/v1/legal/consent", idToken);
}

export function acceptLegalConsent(idToken: string): Promise<LegalConsentResponse> {
  return izfinApiFetch<LegalConsentResponse>("/api/v1/legal/consent", idToken, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ terms_accepted: true, privacy_notice_seen: true }),
  });
}

export function fetchAccountExport(idToken: string): Promise<AccountExportResponse> {
  return izfinApiFetch<AccountExportResponse>(accountExportPath(), idToken);
}

export function deleteAccount(
  idToken: string,
  payload: { email: string; confirmation_phrase: string; irreversible: boolean },
): Promise<AccountDeleteResponse> {
  return izfinApiFetch<AccountDeleteResponse>(accountDeletePath(), idToken, {
    method: "DELETE",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function fetchLegalDocument(path: ReturnType<typeof legalTermsPath> | ReturnType<typeof legalPrivacyPath>): Promise<LegalDocumentResponse> {
  return izfinPublicApiFetch<LegalDocumentResponse>(path);
}

