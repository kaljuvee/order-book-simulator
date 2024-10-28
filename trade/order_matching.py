from collections import defaultdict
from decimal import Decimal
from datetime import datetime
from typing import List, Dict, Optional
import heapq

class Order:
    def __init__(self, order_id: str, symbol: str, side: str, price: Decimal, 
                 quantity: int, timestamp: datetime):
        self.order_id = order_id
        self.symbol = symbol  # Add symbol field
        self.side = side
        self.price = price
        self.quantity = quantity
        self.filled_quantity = 0
        self.status = 'ACTIVE'
        self.timestamp = timestamp

    def __str__(self):
        return (f"Order(id={self.order_id}, symbol={self.symbol}, "
                f"side={self.side}, price={self.price}, "
                f"quantity={self.quantity}, filled={self.filled_quantity}, "
                f"status={self.status})")

class Trade:
    def __init__(self, buy_order_id: str, sell_order_id: str, price: Decimal, quantity: int, timestamp: datetime):
        self.buy_order_id = buy_order_id
        self.sell_order_id = sell_order_id
        self.price = price
        self.quantity = quantity
        self.timestamp = timestamp

    def __repr__(self):
        return f"Trade(buy={self.buy_order_id}, sell={self.sell_order_id}, {self.price} x {self.quantity})"

class OrderBook:
    def __init__(self):
        # Price levels for buy orders (bids)
        self.bids: Dict[Decimal, List[Order]] = defaultdict(list)
        # Price levels for sell orders (asks)
        self.asks: Dict[Decimal, List[Order]] = defaultdict(list)
        # Quick lookup for orders by ID
        self.orders: Dict[str, Order] = {}
        # Store trades
        self.trades: List[Trade] = []
        # Keep track of best bid and ask
        self.best_bid_price: Optional[Decimal] = None
        self.best_ask_price: Optional[Decimal] = None

    def add_order(self, order: Order) -> List[Trade]:
        """Add a new order and return list of trades if any matches occur."""
        if order.order_id in self.orders:
            raise ValueError(f"Order id {order.order_id} already exists")

        self.orders[order.order_id] = order
        trades = []

        if order.side == 'BUY':
            trades = self._match_buy_order(order)
            if order.quantity > 0:  # If order is not fully filled
                self._add_to_bids(order)
        else:  # SELL
            trades = self._match_sell_order(order)
            if order.quantity > 0:  # If order is not fully filled
                self._add_to_asks(order)

        self._update_best_prices()
        return trades

    def cancel_order(self, order_id: str) -> bool:
        """Cancel an existing order. Returns True if successful."""
        if order_id not in self.orders:
            return False

        order = self.orders[order_id]
        if order.status != 'ACTIVE':
            return False

        order.status = 'CANCELLED'
        if order.side == 'BUY':
            self._remove_from_bids(order)
        else:
            self._remove_from_asks(order)

        self._update_best_prices()
        return True

    def _match_buy_order(self, buy_order: Order) -> List[Trade]:
        """Match a buy order against the order book."""
        trades = []
        while buy_order.quantity > 0 and self.asks:
            best_ask_price = min(self.asks.keys())
            if buy_order.price < best_ask_price:
                break

            # Match against best ask price
            sell_orders = self.asks[best_ask_price]
            while sell_orders and buy_order.quantity > 0:
                sell_order = sell_orders[0]
                match_qty = min(buy_order.quantity, sell_order.quantity)
                
                # Create trade
                trade = Trade(
                    buy_order_id=buy_order.order_id,
                    sell_order_id=sell_order.order_id,
                    price=best_ask_price,
                    quantity=match_qty,
                    timestamp=datetime.now()
                )
                trades.append(trade)

                # Update orders
                buy_order.quantity -= match_qty
                buy_order.filled_quantity += match_qty
                sell_order.quantity -= match_qty
                sell_order.filled_quantity += match_qty

                if sell_order.quantity == 0:
                    sell_order.status = 'FILLED'
                    sell_orders.pop(0)
                    if not sell_orders:
                        del self.asks[best_ask_price]

        return trades

    def _match_sell_order(self, sell_order: Order) -> List[Trade]:
        """Match a sell order against the order book."""
        trades = []
        while sell_order.quantity > 0 and self.bids:
            best_bid_price = max(self.bids.keys())
            if sell_order.price > best_bid_price:
                break

            # Match against best bid price
            buy_orders = self.bids[best_bid_price]
            while buy_orders and sell_order.quantity > 0:
                buy_order = buy_orders[0]
                match_qty = min(sell_order.quantity, buy_order.quantity)

                # Create trade
                trade = Trade(
                    buy_order_id=buy_order.order_id,
                    sell_order_id=sell_order.order_id,
                    price=best_bid_price,
                    quantity=match_qty,
                    timestamp=datetime.now()
                )
                trades.append(trade)

                # Update orders
                sell_order.quantity -= match_qty
                sell_order.filled_quantity += match_qty
                buy_order.quantity -= match_qty
                buy_order.filled_quantity += match_qty

                if buy_order.quantity == 0:
                    buy_order.status = 'FILLED'
                    buy_orders.pop(0)
                    if not buy_orders:
                        del self.bids[best_bid_price]

        return trades

    def _add_to_bids(self, order: Order):
        """Add a buy order to the order book."""
        self.bids[order.price].append(order)
        self._update_best_prices()

    def _add_to_asks(self, order: Order):
        """Add a sell order to the order book."""
        self.asks[order.price].append(order)
        self._update_best_prices()

    def _remove_from_bids(self, order: Order):
        """Remove a buy order from the order book."""
        if order.price in self.bids:
            self.bids[order.price] = [o for o in self.bids[order.price] if o.order_id != order.order_id]
            if not self.bids[order.price]:
                del self.bids[order.price]
        self._update_best_prices()

    def _remove_from_asks(self, order: Order):
        """Remove a sell order from the order book."""
        if order.price in self.asks:
            self.asks[order.price] = [o for o in self.asks[order.price] if o.order_id != order.order_id]
            if not self.asks[order.price]:
                del self.asks[order.price]
        self._update_best_prices()

    def _update_best_prices(self):
        """Update the best bid and ask prices."""
        self.best_bid_price = max(self.bids.keys()) if self.bids else None
        self.best_ask_price = min(self.asks.keys()) if self.asks else None

    def get_order_book_snapshot(self) -> dict:
        """Get current state of the order book."""
        return {
            'bids': [(price, sum(o.quantity for o in orders)) for price, orders in sorted(self.bids.items(), reverse=True)],
            'asks': [(price, sum(o.quantity for o in orders)) for price, orders in sorted(self.asks.items())],
            'best_bid': self.best_bid_price,
            'best_ask': self.best_ask_price
        }

# Example usage
def main():
    # Create order book
    book = OrderBook()

    # Create some sample orders
    orders = [
        Order("1", "OPTI", "BUY", "100.50", 10, datetime.now()),
        Order("2", "OPTI", "SELL", "100.60", 5, datetime.now()),
        Order("3", "OPTI", "BUY", "100.55", 7, datetime.now()),
        Order("4", "OPTI", "SELL", "100.50", 3, datetime.now()),  # This should match immediately
    ]

    # Process orders
    print("Processing orders...")
    for order in orders:
        print(f"\nAdding order: {order}")
        trades = book.add_order(order)
        if trades:
            print("Trades executed:")
            for trade in trades:
                print(f"  {trade}")
        
        # Print current order book state
        snapshot = book.get_order_book_snapshot()
        print("\nOrder Book Snapshot:")
        print("Asks (Sell orders):")
        for price, quantity in snapshot['asks']:
            print(f"  {price}: {quantity}")
        print("Bids (Buy orders):")
        for price, quantity in snapshot['bids']:
            print(f"  {price}: {quantity}")
        print(f"Best bid: {snapshot['best_bid']}")
        print(f"Best ask: {snapshot['best_ask']}")

    # Try cancelling an order
    print("\nCancelling order 1...")
    book.cancel_order("1")
    snapshot = book.get_order_book_snapshot()
    print("\nUpdated Order Book Snapshot:")
    print("Bids (Buy orders):")
    for price, quantity in snapshot['bids']:
        print(f"  {price}: {quantity}")

if __name__ == "__main__":
    main()
