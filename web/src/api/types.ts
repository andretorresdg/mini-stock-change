export type OrderSide = "BID" | "ASK";

export type OrderStatus =
  | "OPEN"
  | "PARTIALLY_FILLED"
  | "FILLED"
  | "CANCELED"
  | "EXPIRED";

export interface SubmitOrderRequest {
  client_order_id: string | null;
  document_number: string;
  side: OrderSide;
  valid_until: string | null;
  symbol: string;
  price: number;
  quantity: number;
}

export interface TradeResponse {
  trade_id: string;
  sequence: number;
  symbol: string;
  buyer_order_id: string;
  seller_order_id: string;
  buyer_broker_id: string;
  seller_broker_id: string;
  price: number;
  quantity: number;
}

export interface OrderResponse {
  order_id: string;
  broker_id: string;
  client_order_id: string | null;
  document_number: string;
  side: OrderSide;
  symbol: string;
  price: number;
  quantity: number;
  remaining_quantity: number;
  filled_quantity: number;
  status: OrderStatus;
  valid_until: string | null;
  trades: TradeResponse[];
}

export interface ApiError {
  code: string;
  message: string;
  status: number;
}

export interface BookLevelResponse {
  price: number;
  quantity: number;
}

export interface BookSnapshotResponse {
  symbol: string;
  bids: BookLevelResponse[];
  asks: BookLevelResponse[];
}

export interface MarketTradeResponse {
  trade_id: string;
  sequence: number;
  symbol: string;
  price: number;
  quantity: number;
}

export interface MarketTradesResponse {
  symbol: string;
  trades: MarketTradeResponse[];
}
