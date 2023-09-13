import numpy as np
from quantfreedom.class_practice.enums import (
    AccountState,
    DecreasePosition,
    LeverageType,
    OrderStatus,
    RejectedOrderError,
    StopLossType,
)


class LeverageLong:
    leverage_calculator = None
    liq_hit_checker = None
    order_result_leverage = None
    order_result_liq_price = None

    market_fee_pct = None
    max_leverage = None
    mmr_pct = None
    static_leverage = None

    def __init__(
        self,
        leverage_type: LeverageType,
        sl_type: StopLossType,
        market_fee_pct: float,
        max_leverage: float,
        mmr_pct: float,
        static_leverage: float,
    ):
        self.market_fee_pct = market_fee_pct
        self.max_leverage = max_leverage
        self.mmr_pct = mmr_pct
        self.static_leverage = static_leverage

        if leverage_type == LeverageType.Static:
            self.leverage_calculator = self.set_static_leverage
        elif leverage_type == LeverageType.Dynamic:
            self.leverage_calculator = self.calculate_dynamic_leverage

        if sl_type == StopLossType.Nothing or leverage_type == LeverageType.Nothing:
            self.liq_hit_checker = self.pass_function
        else:
            self.liq_hit_checker = self.check_liq_hit

        # if there is a stop loss then calc liq hit is pass function

    def pass_function(self, **vargs):
        print("Long Order - Liqidation checker - pass_function")
        pass

    def calculate_leverage(
        self,
        account_state: AccountState,
        sl_price: float,
        average_entry: float,
        entry_size: float,
    ):
        return self.leverage_calculator(
            account_state=account_state,
            sl_price=sl_price,
            average_entry=average_entry,
            entry_size=entry_size,
        )

    def __calc_liq_price(
        self,
        entry_size: float,
        leverage: float,
        average_entry: float,
        account_state: AccountState,
    ):
        print("Long Order - Calculate Leverage - __calc_liq_price")

        # Getting Order Cost
        # https://www.bybithelp.com/HelpCenterKnowledge/bybitHC_Article?id=000001064&language=en_US
        initial_margin = entry_size / leverage
        fee_to_open = entry_size * self.market_fee_pct  # math checked
        possible_bankruptcy_fee = (
            entry_size * (leverage - 1) / leverage * self.market_fee_pct
        )
        cash_used_new = (
            initial_margin + fee_to_open + possible_bankruptcy_fee
        )  # math checked

        if (
            cash_used_new > account_state.available_balance * leverage
            or cash_used_new > account_state.available_balance
        ):
            raise RejectedOrderError(order_status=OrderStatus.CashUsedExceed)

        else:
            # liq formula
            # https://www.bybithelp.com/HelpCenterKnowledge/bybitHC_Article?id=000001067&language=en_US
            available_balance_new = account_state.available_balance - cash_used_new
            cash_used_new = account_state.cash_used + cash_used_new
            cash_borrowed_new = account_state.cash_borrowed + entry_size - cash_used_new

            liq_price_new = average_entry * (
                1 - (1 / leverage) + self.mmr_pct
            )  # math checked
        leverage = round(leverage, 2)
        liq_price_new = round(liq_price_new, 2)
        available_balance_new = round(available_balance_new, 2)
        cash_used_new = round(cash_used_new, 2)
        cash_borrowed_new = round(cash_borrowed_new, 2)
        print(
            f"Long Order - Calculate Leverage - leverage= {leverage} liq_price= {liq_price_new}"
        )
        print(
            f"Long Order - Calculate Leverage - available_balance= {available_balance_new}"
        )
        print(
            f"Long Order - Calculate Leverage - cash_used= {cash_used_new} cash_borrowed= {cash_borrowed_new}"
        )
        return (
            leverage,
            liq_price_new,
            available_balance_new,
            cash_used_new,
            cash_borrowed_new,
        )

    def set_static_leverage(
        self,
        account_state: AccountState,
        sl_price: float,
        average_entry: float,
        entry_size: float,
    ):
        print("Long Order - Calculate Leverage - set_static_leverage")
        return self.__calc_liq_price(
            entry_size=entry_size,
            leverage=self.static_leverage,
            average_entry=average_entry,
            account_state=account_state,
        )

    def calculate_dynamic_leverage(
        self,
        account_state: AccountState,
        sl_price: float,
        average_entry: float,
        entry_size: float,
    ):
        print("Long Order - Calculate Leverage - calculate_dynamic_leverage")
        leverage = round(
            -average_entry
            / (
                sl_price
                - sl_price * 0.001
                - average_entry
                - self.market_fee_pct * average_entry
                # TODO: revisit the .001 to add to the sl if you make this backtester have the ability to go live
            ),
            1,
        )
        if leverage > self.max_leverage:
            leverage = self.max_leverage
        elif leverage < 1:
            leverage = 1

        return self.__calc_liq_price(
            entry_size=entry_size,
            leverage=leverage,
            average_entry=average_entry,
            account_state=account_state,
        )

    def check_liq_hit(self, **vargs):
        print("Long Order - Liqidation Hit Checker - check_liq_hit")