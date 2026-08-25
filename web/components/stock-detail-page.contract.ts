import { StockDetailPage } from "./stock-detail-page";
import { stockDetailHref } from "../lib/stock-detail-route";

type Props = Parameters<typeof StockDetailPage>[0];

const props: Props = { jobId: "job-1", ticker: "THYAO.IS" };
const href: string = stockDetailHref("job-1", "THYAO.IS");

void props;
void href;
