import { Navigate, type RouteObject } from "react-router-dom";
import Layout from "../components/Layout";
import MarketPage from "../pages/MarketPage";
import OrderStatusPage from "../pages/OrderStatusPage";
import SubmitOrderPage from "../pages/SubmitOrderPage";

export const routes: RouteObject[] = [
  {
    path: "/",
    element: <Layout />,
    children: [
      { index: true, element: <Navigate to="/submit-order" replace /> },
      { path: "submit-order", element: <SubmitOrderPage /> },
      { path: "status", element: <OrderStatusPage /> },
      { path: "market", element: <MarketPage /> },
    ],
  },
];
