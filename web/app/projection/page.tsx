import { ProjectionPage } from "../../components/projection-page";

type ProjectionRouteProps = {
  searchParams: Promise<{
    job_id?: string | string[];
    ticker?: string | string[];
  }>;
};

function first(value: string | string[] | undefined): string {
  return Array.isArray(value) ? (value[0] ?? "") : (value ?? "");
}

export default async function ProjectionRoute({ searchParams }: ProjectionRouteProps) {
  const query = await searchParams;
  return <ProjectionPage jobId={first(query.job_id)} ticker={first(query.ticker)} />;
}
