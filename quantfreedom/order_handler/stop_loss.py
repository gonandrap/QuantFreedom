from math import floor
import numpy as np
from quantfreedom.custom_logger import CustomLogger

from quantfreedom.enums import (
    CandleBodyType,
    DecreasePosition,
    MoveStopLoss,
    OrderStatus,
    SLToBeZeroOrEntryType,
    StopLossStrategyType,
)


class StopLossLong:
    sl_price_getter = None
    sl_hit_checker = None
    sl_to_be_price_getter = None
    tsl_price_getter = None

    sl_based_on_lookback = None
    sl_based_on_add_pct = None
    sl_to_be_move_when_pct = None
    sl_to_be_z_or_e = None
    trail_sl_when_pct_from_candle_body = None
    trail_sl_by_pct = None

    market_fee_pct = None

    sl_price = None

    def __init__(
        self,
        sl_based_on_add_pct: float,
        sl_based_on_lookback: int,
        sl_candle_body_type: CandleBodyType,
        sl_to_be_based_on_candle_body_type: CandleBodyType,
        sl_to_be_when_pct_from_candle_body: float,
        sl_to_be_zero_or_entry_type: int,
        sl_type: int,
        trail_sl_based_on_candle_body_type: CandleBodyType,
        trail_sl_by_pct: float,
        trail_sl_when_pct_from_candle_body: float,
        market_fee_pct: float,
        logger: CustomLogger,
    ):
        # variables
        self.sl_to_be_when_pct_from_candle_body = sl_to_be_when_pct_from_candle_body
        self.sl_to_be_move_when_pct = sl_to_be_when_pct_from_candle_body
        self.trail_sl_when_pct_from_candle_body = trail_sl_when_pct_from_candle_body
        self.trail_sl_by_pct = trail_sl_by_pct
        self.sl_based_on_lookback = sl_based_on_lookback
        self.sl_based_on_add_pct = sl_based_on_add_pct
        self.market_fee_pct = market_fee_pct
        self.info_logger = logger.info_logger

        # setting up stop loss calulator
        if sl_type == StopLossStrategyType.SLBasedOnCandleBody:
            self.calculator = self.sl_based_on_candle_body_calc
            if sl_candle_body_type == CandleBodyType.Open:
                self.sl_price_getter = self.__get_candle_body_price_open
            elif sl_candle_body_type == CandleBodyType.High:
                self.sl_price_getter = self.__get_candle_body_price_high
            elif sl_candle_body_type == CandleBodyType.Low:
                self.sl_price_getter = self.__get_candle_body_price_low
            elif sl_candle_body_type == CandleBodyType.Close:
                self.sl_price_getter = self.__get_candle_body_price_close
            else:
                raise ValueError("Something is wrong with your stop loss type")
            self.sl_hit_checker = self.check_stop_loss_hit
        elif sl_type == StopLossStrategyType.SLPct:
            self.calculator = self.sl_pct_calc
            self.sl_hit_checker = self.check_stop_loss_hit
        elif sl_type == StopLossStrategyType.Nothing:
            self.calculator = self.pass_function
            self.sl_hit_checker = self.pass_function

        # setting up stop loss break even checker
        if sl_to_be_based_on_candle_body_type == CandleBodyType.Nothing:
            self.sl_to_be_price_getter = self.pass_function
            self.move_sl_to_be_checker = self.pass_function
        elif sl_to_be_based_on_candle_body_type == CandleBodyType.Open:
            self.sl_to_be_price_getter = self.__get_candle_body_price_open
            self.move_sl_to_be_checker = self.check_move_stop_loss_to_be
        elif sl_to_be_based_on_candle_body_type == CandleBodyType.High:
            self.sl_to_be_price_getter = self.__get_candle_body_price_high
            self.move_sl_to_be_checker = self.check_move_stop_loss_to_be
        elif sl_to_be_based_on_candle_body_type == CandleBodyType.Low:
            self.sl_to_be_price_getter = self.__get_candle_body_price_low
            self.move_sl_to_be_checker = self.check_move_stop_loss_to_be
        elif sl_to_be_based_on_candle_body_type == CandleBodyType.Close:
            self.sl_to_be_price_getter = self.__get_candle_body_price_close
            self.move_sl_to_be_checker = self.check_move_stop_loss_to_be

        # setting up stop loss be zero or entry
        if sl_to_be_zero_or_entry_type != SLToBeZeroOrEntryType.Nothing:
            if sl_to_be_zero_or_entry_type == SLToBeZeroOrEntryType.ZeroLoss:
                self.sl_to_be_z_or_e = self.__sl_to_be_zero
            elif sl_to_be_zero_or_entry_type == SLToBeZeroOrEntryType.AverageEntry:
                self.sl_to_be_z_or_e = self.__sl_to_be_entry

        # setting up stop loss break even checker
        if trail_sl_based_on_candle_body_type == CandleBodyType.Nothing:
            self.tsl_price_getter = self.pass_function
            self.move_tsl_checker = self.pass_function
        elif trail_sl_based_on_candle_body_type == CandleBodyType.Open:
            self.tsl_price_getter = self.__get_candle_body_price_open
            self.move_tsl_checker = self.check_move_trailing_stop_loss
        elif trail_sl_based_on_candle_body_type == CandleBodyType.High:
            self.tsl_price_getter = self.__get_candle_body_price_high
            self.move_tsl_checker = self.check_move_trailing_stop_loss
        elif trail_sl_based_on_candle_body_type == CandleBodyType.Low:
            self.tsl_price_getter = self.__get_candle_body_price_low
            self.move_tsl_checker = self.check_move_trailing_stop_loss
        elif trail_sl_based_on_candle_body_type == CandleBodyType.Close:
            self.tsl_price_getter = self.__get_candle_body_price_close
            self.move_tsl_checker = self.check_move_trailing_stop_loss

    def __get_candle_body_price_open(self, lookback, bar_index, candles):
        self.info_logger.debug(f"")
        return candles[lookback:bar_index, 0].min()

    def __get_candle_body_price_high(self, lookback, bar_index, candles):
        self.info_logger.debug(f"")
        return candles[lookback:bar_index, 1].min()

    def __get_candle_body_price_low(self, lookback, bar_index, candles):
        self.info_logger.debug(f"")
        return candles[lookback:bar_index, 2].min()

    def __get_candle_body_price_close(self, lookback, bar_index, candles):
        self.info_logger.debug(f"")
        return candles[lookback:bar_index, 3].min()

    # main functions
    def pass_function(self, **vargs):
        pass

    def sl_based_on_candle_body_calc(self, bar_index, candles):
        self.info_logger.debug(f"")
        # lb will be bar index if sl isn't based on lookback because look back will be 0
        lookback = max(int((bar_index - 1) - self.sl_based_on_lookback), 0)
        candle_body = self.sl_price_getter(
            lookback=lookback,
            bar_index=bar_index,
            candles=candles,
        )
        self.sl_price = float(floor(candle_body - (candle_body * self.sl_based_on_add_pct)))
        return self.sl_price

    # stop loss to break even zero or entry
    def __sl_to_be_zero(self, average_entry):
        self.info_logger.debug(f"")
        return (self.market_fee_pct * average_entry + average_entry) / (1 - self.market_fee_pct)

    def __sl_to_be_entry(self, average_entry):
        self.info_logger.debug(f"")
        return average_entry

    def check_move_stop_loss_to_be(
        self,
        average_entry,
        bar_index,
        candles,
        can_move_sl_to_be,
    ):
        self.info_logger.debug(f"")
        if can_move_sl_to_be:
            self.info_logger.debug(f"Can move sl to break even")
            # Stop Loss to break even
            candle_body_ohlc = self.sl_to_be_price_getter(
                lookback=bar_index,
                bar_index=bar_index + 1,
                candles=candles,
            )
            pct_from_ae = (candle_body_ohlc - average_entry) / average_entry
            move_sl = pct_from_ae > self.sl_to_be_move_when_pct
            if move_sl:
                self.info_logger.debug(f"Move sl true")
                self.sl_price = self.sl_to_be_z_or_e(average_entry)
                raise MoveStopLoss(
                    sl_price=self.sl_price,
                    order_status=OrderStatus.MovedStopLossToBE,
                )

    def check_move_trailing_stop_loss(
        self,
        average_entry,
        bar_index,
        candles,
    ):
        self.info_logger.debug("")
        candle_body_ohlc = self.tsl_price_getter(
            lookback=bar_index,
            bar_index=bar_index + 1,
            candles=candles,
        )
        pct_from_ae = (candle_body_ohlc - average_entry) / average_entry
        move_sl = pct_from_ae > self.trail_sl_when_pct_from_candle_body
        if move_sl:
            temp_sl_price = candle_body_ohlc - candle_body_ohlc * self.trail_sl_by_pct
            if temp_sl_price > self.sl_price:
                self.info_logger.debug(f"temp sl {temp_sl_price} > sl price {self.sl_price} - Will move trailing stop")
                self.sl_price = temp_sl_price
                raise MoveStopLoss(
                    sl_price=self.sl_price,
                    order_status=OrderStatus.MovedTrailingStopLoss,
                )
            else:
                self.info_logger.debug(f"temp sl {temp_sl_price} < sl price {self.sl_price} - Wont move trailing stop")

    def check_stop_loss_hit(self, sl_hit: bool, exit_fee_pct: float):
        self.info_logger.debug("")
        if sl_hit:
            self.info_logger.debug(f"Stop loss hit true")
            raise DecreasePosition(
                exit_price=self.sl_price,
                order_status=OrderStatus.StopLossFilled,
                exit_fee_pct=exit_fee_pct,
            )

    def sl_pct_calc(self, **vargs):
        pass