import OrderLookupForm from "../features/orders/OrderLookupForm";

export default function OrderStatusPage() {
  return (
    <section aria-labelledby="order-status-heading" className="page-section">
      <h1 id="order-status-heading" className="page-heading">
        Order Status
      </h1>
      <OrderLookupForm />
    </section>
  );
}
