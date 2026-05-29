import SubmitOrderForm from "../features/orders/SubmitOrderForm";

export default function SubmitOrderPage() {
  return (
    <section aria-labelledby="submit-order-heading" style={{ maxWidth: "560px" }}>
      <h1
        id="submit-order-heading"
        style={{ marginBottom: "1.5rem", fontSize: "1.5rem" }}
      >
        Submit Order
      </h1>
      <SubmitOrderForm />
    </section>
  );
}
