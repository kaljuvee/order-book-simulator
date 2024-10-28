## Order Matching Simulator

The Order Matching Simulator demonstrates how a basic order matching engine works in financial markets. It allows you to:

### Key Features
* Place limit and market orders for various symbols
* View real-time order book depth
* Cancel active orders
* Track order history and execution status
* See trade executions and fills

### Pre-populated OPTI Order Book
The simulator comes with a pre-populated order book for OPTI token with the following orders:
* Sell orders: $1.20 (1000 units), $1.15 (500 units), $1.10 (750 units)
* Buy orders: $1.05 (800 units), $1.00 (1000 units), $0.95 (600 units)

### How to Use

1. **Placing Orders:**
   * Select order type (LIMIT or MARKET)
   * Choose BUY or SELL side
   * For limit orders: Enter your desired price
   * For market orders: System will match at best available price
   * Enter quantity
   * Submit order

2. **Order Matching Rules:**
   * Limit orders: Only match when price conditions are met
   * Market buy orders: Match against lowest available sell orders
   * Market sell orders: Match against highest available buy orders
   * Orders can be partially filled if full quantity isn't available

3. **Order Book Display:**
   * View current bids (buy orders) and asks (sell orders)
   * Monitor best bid and ask prices
   * Track order history and execution status

## References
* Learn about [order matching engines](https://www.investopedia.com/terms/m/matching-engine.asp)
* Understanding [market orders vs limit orders](https://www.investopedia.com/ask/answers/100314/whats-difference-between-market-order-and-limit-order.asp)