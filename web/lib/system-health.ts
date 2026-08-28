import { izfinPublicApiFetch } from "./api";

export type SystemReadinessResponse = {
  ready: boolean;
  authentication: boolean;
  user_repository: boolean;
  signal_repository: boolean;
  scan_runner: boolean;
  scan_job_store: boolean;
  scan_job_persistence: boolean;
};

export function fetchSystemReadiness(): Promise<SystemReadinessResponse> {
  return izfinPublicApiFetch<SystemReadinessResponse>("/api/v1/health/ready/durable");
}
