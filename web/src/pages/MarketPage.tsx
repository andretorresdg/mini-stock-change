import MarketView from "../features/market/MarketView";

export default function MarketPage() {
  return (
    <section aria-labelledby="market-heading" className="page-section">
      <h1 id="market-heading" className="page-heading">
        Market Data
      </h1>
      <MarketView />
    </section>
  );
}
