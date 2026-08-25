import type { ComponentProps } from "react";
import { AccountPage } from "./account-page";
import {
  accountDeletePath,
  accountExportPath,
  legalPrivacyPath,
  legalTermsPath,
  type AccountDeleteResponse,
  type LegalDocumentResponse,
} from "../lib/account";

const props: ComponentProps<typeof AccountPage> = {};
const deletePath: "/api/v1/account" = accountDeletePath();
const exportPath: "/api/v1/account/export" = accountExportPath();
const termsPath: "/api/v1/legal/terms" = legalTermsPath();
const privacyPath: "/api/v1/legal/privacy" = legalPrivacyPath();
const deleted: AccountDeleteResponse = { deleted: true, deleted_documents: 2 };
const legal: LegalDocumentResponse = { version: "v1", markdown: "# Metin", warning: null, info: null };

void props;
void deletePath;
void exportPath;
void termsPath;
void privacyPath;
void deleted;
void legal;
