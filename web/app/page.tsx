import { HomeDecisionCenter } from "../components/home-decision-center";
import { MarketStrip } from "../components/market-strip";

export default function Home() {
  return (
    <main id="top" className="command-page">
      <MarketStrip />
      <HomeDecisionCenter />
    </main>
  );
}
