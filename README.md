# Simple Stock Exchange

A command-line based stock exchange engine implemented in Python. It supports Limit and Market orders, maintains an Order Book for multiple symbols, and performs automatic order matching based on price-time priority.

## Features

-   **Order Types:** Supports `LIMIT` (LMT) and `MARKET` (MKT) orders.
-   **Order Book:** Maintains sorted bids and asks for each symbol independently.
-   **Matching Engine:** Automatically matches buy and sell orders.
-   **Status Tracking:** Tracks order status (`PENDING`, `PARTIAL`, `FILLED`) in real-time.
-   **Type Safety:** Uses Python `typing` and `Enums` for robust and readable code.
-   **Precision:** Uses `decimal.Decimal` for all monetary calculations to avoid floating-point errors common in financial software.

## Requirements

-   Python 3.7+ (Required for `@dataclass` support).
-   No external libraries required (uses standard library only).

## How to Run

1.  Open your terminal.
2.  Navigate to the project directory.
3.  Run the application using the following command:

        python main.py

### Sample Usage

Once the program is running, you can enter commands:


    BUY SNAP LMT $30 100
    BUY FB MKT 20
    VIEW ORDERS
    SELL SNAP LMT $30.00 20
    QUOTE SNAP
    QUIT


## How to Run Tests

The project includes a suite of unit tests (`test_stock.py`) covering the Order Book sorting logic, Matching engine execution, and Order status updates.

To run the tests:

    python test_stock.py


## Architecture & Design Choices

The application is built using **Object-Oriented Programming (OOP)** principles and strictly follows **SOLID** concepts to ensure maintainability, legibility, and refactorability.

### Key Components

1.  **`Order` (Dataclass)**
    Represents a single order entity.
    -   **Design Choice:** I used `@property` for the `status` field. Instead of manually updating a status string (which leads to data inconsistency), the status is dynamically calculated based on `filled` vs `qty`. This ensures a Single Source of Truth.

2.  **`OrderBook`**
    Encapsulates the logic for a specific trading symbol.
    -   **Sorting:** It maintains two lists (`bids` and `asks`). Bids are sorted by price descending (highest buy first), and Asks are sorted by price ascending (lowest sell first).
    -   **Matching:** The matching logic resides here, adhering to the principle of "Information Expert" — the class containing the data should be responsible for processing it.

3.  **`Exchange`**
    Acts as a Facade. It parses user input, routes commands to the correct `OrderBook`, and handles output. It does not contain low-level matching logic, keeping the class clean.

4.  **Decimal vs Float**
    All prices are stored as `decimal.Decimal` to ensure financial precision and avoid binary floating-point arithmetic errors (e.g., `0.1 + 0.2 != 0.3`).

### Assumptions

-   **Market Orders Priority:** Market Orders are treated as having "Infinite" price priority for Buys and "Zero" price priority for Sells during sorting. This ensures they are always at the top of the Order Book execution queue.
-   **Execution Price:** When a Limit Order matches with a Market Order, the trade executes at the Limit Order's price (Maker's price).
