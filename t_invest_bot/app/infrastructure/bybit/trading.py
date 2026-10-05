from dataclasses import dataclass
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR
from uuid import uuid4

from domain.order_execution import BrokerActiveOrder, PlacedOrder
from domain.order_state import OrderExecutionState
from infrastructure.bybit.client import BybitClient, to_decimal


def positive(value, name: str) -> Decimal:
    number = Decimal(str(value))
    if not number.is_finite() or number <= 0:
        raise ValueError(f"Invalid Bybit {name}")
    return number


@dataclass(slots=True)
class BybitTradingGateway:
    client: BybitClient
    rules: dict[str, dict]

    def _rule(self, symbol: str) -> dict:
        if symbol not in self.rules:
            raise ValueError(f"Bybit asset is not part of this session: {symbol}")
        return self.rules[symbol]

    def _place(self, symbol: str, side: str, quantity: int | Decimal, price: Decimal | None) -> PlacedOrder:
        rule = self._rule(symbol)
        quantity = positive(quantity, "quantity")
        step = positive(rule["quantity_step"], "quantity step")
        if side == "Sell":
            quantity = (quantity / step).to_integral_value(rounding=ROUND_FLOOR) * step
        if quantity % step != 0 or quantity <= 0 or quantity < to_decimal(rule["min_quantity"]):
            raise ValueError("Bybit quantity does not satisfy exchange restrictions; остаток ниже шага биржи нельзя продать автоматически")
        body = {
            "category": "spot", "symbol": symbol, "side": side,
            "orderType": "Market" if price is None else "Limit",
            "qty": format(quantity, "f"), "orderLinkId": "esm-" + uuid4().hex,
            "isLeverage": 0, "orderFilter": "Order",
        }
        if price is not None:
            tick = positive(rule["price_step"], "price step")
            price = positive(price, "price")
            rounding = ROUND_FLOOR if side == "Buy" else ROUND_CEILING
            price = (price / tick).to_integral_value(rounding=rounding) * tick
            if price <= 0 or price * quantity < to_decimal(rule["min_order_amount"]):
                raise ValueError("Bybit order value is below the exchange minimum")
            body.update(price=format(price, "f"), timeInForce="GTC")
        else:
            body.update(marketUnit="baseCoin", timeInForce="IOC")
        response = self.client.place_spot_order(body)
        order_id = str(response.get("orderId") or "")
        if not order_id:
            raise ValueError("Bybit did not acknowledge an order ID")
        return PlacedOrder(order_id, str(body["orderLinkId"]), "STOP_MARKET" if price is None else None)

    def place_limit_buy(self, account_id: str, instrument_id: str, quantity: int | Decimal, price: Decimal) -> PlacedOrder:
        return self._place(instrument_id, "Buy", quantity, price)

    def place_limit_sell(self, account_id: str, instrument_id: str, quantity: int | Decimal, price: Decimal) -> PlacedOrder:
        return self._place(instrument_id, "Sell", quantity, price)

    def place_market_sell(self, account_id: str, instrument_id: str, quantity: int | Decimal) -> PlacedOrder:
        return self._place(instrument_id, "Sell", quantity, None)

    def cancel_order(self, account_id: str, order_id: str) -> None:
        rows = self.client.get_spot_orders(order_id=order_id)
        if not rows:
            rows = self.client.get_spot_orders(order_id=order_id, history=True)
        if not rows:
            raise ValueError("Bybit order not found; cancellation is not confirmed")
        self.client.cancel_spot_order(str(rows[0]["symbol"]), order_id)

    def has_active_order(self, account_id: str, instrument_id: str) -> bool:
        return bool(self.client.get_spot_orders(symbol=instrument_id))

    def list_active_orders(self, account_id: str) -> list[BrokerActiveOrder]:
        return [BrokerActiveOrder(
            str(row["orderId"]), str(row["symbol"]), str(row["side"]).upper(),
            to_decimal(row["qty"]), to_decimal(row.get("price")),
        ) for row in self.client.get_spot_orders() if row.get("symbol") in self.rules and str(row.get("orderLinkId") or "").startswith("esm-")]

    def get_order_state(self, account_id: str, order_id: str) -> OrderExecutionState:
        rows = self.client.get_spot_orders(order_id=order_id)
        if not rows:
            rows = self.client.get_spot_orders(order_id=order_id, history=True)
        if not rows:
            return OrderExecutionState(order_id, False, 0)
        row = rows[0]
        statuses = {"Filled": "FILLED", "Cancelled": "CANCELLED", "PartiallyFilledCanceled": "CANCELLED", "Rejected": "REJECTED", "Deactivated": "CANCELLED", "New": "NEW", "PartiallyFilled": "PARTIALLY_FILLED"}
        status = statuses.get(str(row.get("orderStatus")), "UNKNOWN")
        quantity = to_decimal(row.get("cumExecQty"))
        total = to_decimal(row.get("cumExecValue"))
        commission = Decimal("0")
        base_fee = Decimal("0")
        if quantity > 0:
            rule = self._rule(str(row["symbol"]))
            executions = {str(item["execId"]): item for item in self.client.get_spot_executions(order_id)}
            if sum((to_decimal(item.get("execQty")) for item in executions.values()), Decimal("0")) != quantity:
                return OrderExecutionState(order_id, False, 0, status="UNKNOWN")
            for item in executions.values():
                fee = to_decimal(item.get("execFee"))
                currency = str(item.get("feeCurrency") or "")
                if not fee:
                    continue
                if currency == rule["quote_coin"]:
                    commission += fee
                elif currency == rule["base_coin"]:
                    commission += fee * positive(item["execPrice"], "execution price")
                    base_fee += fee
                else:
                    tickers = self.client.get_tickers(symbol=currency + str(rule["quote_coin"]))
                    if not tickers:
                        raise ValueError("Cannot value Bybit fee currency")
                    commission += fee * positive(tickers[0]["lastPrice"], "fee conversion price")
            price = positive(total / quantity, "execution price")
            if row["side"] == "Buy":
                quantity -= base_fee
                total -= base_fee * price
            elif base_fee:
                raise ValueError("Bybit SELL charged in base coin requires reconciliation")
        else:
            price = None
        return OrderExecutionState(
            order_id, status == "FILLED", quantity, price, commission, total,
            status, status == "CANCELLED", status == "REJECTED",
        )

    def get_best_bid_ask(self, instrument_uid: str) -> tuple[Decimal, Decimal]:
        rows = self.client.get_tickers(symbol=instrument_uid)
        if not rows:
            raise ValueError("Bybit ticker unavailable")
        return positive(rows[0]["bid1Price"], "bid"), positive(rows[0]["ask1Price"], "ask")

    def get_order_book_quote(self, instrument_uid: str):
        from infrastructure.tinvest.last_price_provider import OrderBookQuote

        bid, ask = self.get_best_bid_ask(instrument_uid)
        return OrderBookQuote(instrument_uid, bid, ask)

    def get_last_price(self, instrument_uid: str) -> Decimal:
        rows = self.client.get_tickers(symbol=instrument_uid)
        if not rows:
            raise ValueError("Bybit ticker unavailable")
        return positive(rows[0]["lastPrice"], "last price")

    def get_mid_price(self, instrument_uid: str) -> Decimal:
        bid, ask = self.get_best_bid_ask(instrument_uid)
        return (bid + ask) / 2

    def get_available_cash(self, currency: str) -> Decimal:
        coins = self.client.get_wallet_balance().get("coin") or []
        coin = next((item for item in coins if item.get("coin") == currency), None)
        if coin is None:
            return Decimal("0")
        cash = to_decimal(coin.get("walletBalance")) - to_decimal(coin.get("locked")) - to_decimal(coin.get("borrowAmount"))
        if not cash.is_finite():
            raise ValueError("Invalid Bybit available balance")
        return max(Decimal("0"), cash)
