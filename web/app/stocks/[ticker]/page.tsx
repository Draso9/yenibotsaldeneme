import { StockDetailPage } from "../../../components/stock-detail-page";

type StockRouteProps = {
  params: Promise<{ ticker: string }>;
  searchParams: Promise<{ job_id?: string | string[] }>;
};

export default async function StockRoute({ params, searchParams }: StockRouteProps) {
  const { ticker } = await params;
  const query = await searchParams;
  const jobId = Array.isArray(query.job_id) ? (query.job_id[0] ?? "") : (query.job_id ?? "");

  return <main id="top"><StockDetailPage jobId={jobId} ticker={ticker} /></main>;
}
