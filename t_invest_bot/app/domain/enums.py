from enum import Enum


class AccountStatus(str, Enum):
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    STOP_NEW_GRIDS = "STOP_NEW_GRIDS"
    EMERGENCY_CLOSE = "EMERGENCY_CLOSE"
    CLOSED = "CLOSED"


class PortfolioMode(str, Enum):
    MANUAL = "MANUAL"
    INDEX = "INDEX"
    CUSTOM = "CUSTOM"


class GridStatus(str, Enum):
    CREATED = "CREATED"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    FINISH_ONLY = "FINISH_ONLY"
    CLOSING = "CLOSING"
    CLOSED = "CLOSED"
    EMERGENCY_CLOSING = "EMERGENCY_CLOSING"


class GridLevelStatus(str, Enum):
    WAITING_PRICE = "WAITING_PRICE"
    TRAILING_ENTRY = "TRAILING_ENTRY"
    WAITING_FOR_FUNDS = "WAITING_FOR_FUNDS"
    ORDER_PLACED = "ORDER_PLACED"
    POSITION_OPENED = "POSITION_OPENED"
    CLOSED = "CLOSED"
    SKIPPED = "SKIPPED"


class PositionStatus(str, Enum):
    WAITING_ENTRY = "WAITING_ENTRY"
    ENTRY_ORDER_PLACED = "ENTRY_ORDER_PLACED"
    OPEN = "OPEN"
    TRAILING_EXIT = "TRAILING_EXIT"
    EXIT_ORDER_PLACED = "EXIT_ORDER_PLACED"
    CLOSED = "CLOSED"
    FORCE_CLOSING = "FORCE_CLOSING"


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    LIMIT = "LIMIT"
    MARKET = "MARKET"


class OrderStatus(str, Enum):
    NEW = "NEW"
    PLACED = "PLACED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"


class NotificationSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class InstrumentType(str, Enum):
    STOCK = "STOCK"
    ETF = "ETF"
    BOND = "BOND"
    CURRENCY = "CURRENCY"
    FUND = "FUND"
    FUTURE = "FUTURE"


class InstrumentStatus(str, Enum):
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"
    FINISH_ONLY = "FINISH_ONLY"
    LEFT_INDEX_STOP_NEW = "LEFT_INDEX_STOP_NEW"
    NEW_PENDING_APPROVAL = "NEW_PENDING_APPROVAL"


class TradingMode(str, Enum):
    SPOT = "SPOT"


class DirectionMode(str, Enum):
    LONG_ONLY = "LONG_ONLY"