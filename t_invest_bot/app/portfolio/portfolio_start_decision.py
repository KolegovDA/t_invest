from dataclasses import dataclass
from decimal import Decimal


@dataclass(slots=True)
class PortfolioStartDecision:
    can_start: bool
    is_underfunded: bool
    warning: str | None = None


class PortfolioStartDecisionService:
    def decide(
        self,
        available_cash: Decimal,
        required_deposit: Decimal,
        allow_underfunded_start: bool,
    ) -> PortfolioStartDecision:
        if available_cash >= required_deposit:
            return PortfolioStartDecision(
                can_start=True,
                is_underfunded=False,
            )

        if allow_underfunded_start:
            return PortfolioStartDecision(
                can_start=True,
                is_underfunded=True,
                warning=(
                    "Недостаточно средств для полного покрытия сетки. "
                    "Запуск разрешен пользователем. "
                    "Если на очередной ордер не хватит денег, покупка будет пропущена до пополнения."
                ),
            )

        return PortfolioStartDecision(
            can_start=False,
            is_underfunded=True,
            warning=(
                "Недостаточно средств для запуска сетки. "
                "Уменьшите количество активов, количество уровней или пополните счет."
            ),
        )
