import SubmitOrderForm from "../features/orders/SubmitOrderForm";

export default function SubmitOrderPage() {
  return (
    <section aria-labelledby="submit-order-heading" className="page-section">
      <h1 id="submit-order-heading" className="page-heading">
        Submit Order
      </h1>
      <SubmitOrderForm />
    </section>
  );
}
