import OrderLookupForm from "../features/orders/OrderLookupForm";

export default function OrderStatusPage() {
  return (
    <section aria-labelledby="order-status-heading" style={{ maxWidth: "600px" }}>
      <h1
        id="order-status-heading"
        style={{ marginBottom: "1.5rem", fontSize: "1.5rem" }}
      >
        Order Status
      </h1>
      <OrderLookupForm />
    </section>
  );
}
