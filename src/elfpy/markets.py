"""
Market simulators store state information when interfacing AMM pricing models with users

TODO: rewrite all functions to have typed inputs
"""

import numpy as np
import elfpy.utils.time as time_utils

# Currently many functions use >5 arguments.
# These should be packaged up into shared variables, e.g.
#     reserves = (in_reserves, out_reserves)
#     share_prices = (init_share_price, share_price)
# pylint: disable=too-many-arguments


class Market:
    """
    Holds state variables for market simulation and executes trades.

    The Market class executes trades by updating market variables according to the given pricing model.
    It also has some helper variables for assessing pricing model values given market conditions.
    """

    # TODO: set up member object that owns attributes instead of so many individual instance attributes
    # pylint: disable=too-many-instance-attributes

    def __init__(
        self,
        share_reserves,
        bond_reserves,
        fee_percent,
        token_duration,
        pricing_model,
        time_stretch_constant=1,
        init_share_price=1,
        share_price=1,
        verbose=False,
    ):
        # TODO: In order for the AMM to work as expected we should store
        # a share reserve instead of a base reserve.
        self.time = 0  # time in year fractions
        self.share_reserves = share_reserves  # z
        self.bond_reserves = bond_reserves  # y
        self.fee_percent = fee_percent  # g
        self.init_share_price = init_share_price  # u normalizing constant
        self.share_price = share_price  # c
        self.token_duration = token_duration  # how long does a token last before expiry
        self.pricing_model = pricing_model
        self.time_stretch_constant = time_stretch_constant
        self.base_asset_orders = 0
        self.token_asset_orders = 0
        self.base_asset_volume = 0
        self.token_asset_volume = 0
        self.cum_token_asset_slippage = 0
        self.cum_base_asset_slippage = 0
        self.cum_token_asset_fees = 0
        self.cum_base_asset_fees = 0
        self.spot_price = 0
        self.total_supply = self.share_reserves + self.bond_reserves
        self.verbose = verbose

    def get_target_reserves(self, token_in, trade_direction):
        """
        Determine which asset is the target based on token_in and trade_direction
        """
        if trade_direction == "in":
            if token_in == "fyt":
                target_reserves = self.bond_reserves
            else:
                target_reserves = self.share_reserves
        elif trade_direction == "out":
            if token_in == "fyt":
                target_reserves = self.share_reserves
            else:
                target_reserves = self.bond_reserves
        return target_reserves

    def check_fees(
        self,
        amount,
        tokens,
        reserves,
        trade_results,
    ):
        """Checks fee values for out of bounds and prints verbose outputs"""
        (token_in, token_out) = tokens
        (in_reserves, out_reserves) = reserves
        (
            without_fee_or_slippage,
            output_with_fee,
            output_without_fee,
            fee,
        ) = trade_results
        if (
            any(
                [
                    isinstance(output_with_fee, complex),
                    isinstance(output_without_fee, complex),
                    isinstance(fee, complex),
                ]
            )
            or fee < 0
        ):
            state_string = self.get_market_state_string()
            assert False, (
                f"Market.check_fees: Error: fee={fee} should not be < 0 and the type should not be complex."
                + f"\ntoken_in = {token_in}"
                + f"\ntoken_out = {token_out}"
                + f"\nin_reserves = {in_reserves}"
                + f"\nout_reserves = {out_reserves}"
                + f"\ntrade_amount = {amount}"
                + f"\nwithout_fee_or_slippage = {without_fee_or_slippage}"
                + f"\noutput_with_fee = {output_with_fee}"
                + f"\noutput_without_fee = {output_without_fee}\n"
                + state_string
            )

    def update_market(self, market_deltas):
        """
        Increments member variables to reflect current market conditions
        """
        for key, value in market_deltas.items():
            assert np.isfinite(value), f"markets.update_market: ERROR: market delta key {key} is not finite."
        self.share_reserves += market_deltas["d_base_asset"]
        self.bond_reserves += market_deltas["d_token_asset"]
        self.cum_base_asset_slippage += market_deltas["d_base_asset_slippage"]
        self.cum_token_asset_slippage += market_deltas["d_token_asset_slippage"]
        self.cum_base_asset_fees += market_deltas["d_base_asset_fee"]
        self.cum_token_asset_fees += market_deltas["d_token_asset_fee"]
        self.base_asset_orders += market_deltas["d_base_asset_orders"]
        self.token_asset_orders += market_deltas["d_token_asset_orders"]
        self.base_asset_volume += market_deltas["d_base_asset_volume"]
        self.token_asset_volume += market_deltas["d_token_asset_volume"]

    def swap(self, user_action):
        """
        Execute a trade in the simulated market.
        """
        # assign general trade details, irrespective of trade type
        user_action.fee_percent = self.fee_percent
        user_action.init_share_price = self.init_share_price
        user_action.share_price = self.share_price
        user_action.share_reserves = self.share_reserves
        user_action.bond_reserves = self.bond_reserves
        # for each position, specify how to forumulate trade and then execute
        if user_action.action_type == "open_long":  # buy to open long
            user_action.direction = "out"  # calcOutGivenIn
            user_action.token_out = "pt"  # buy unknown PT with known base
            market_deltas, wallet_deltas = self.pricing_model.open_long(user_action)
        elif user_action.action_type == "close_long":  # sell to close long
            user_action.direction = "out"  # calcOutGivenIn
            user_action.token_out = "base"  # sell known PT for unkonwn base
            market_deltas, wallet_deltas = self.pricing_model.close_long(user_action)
        elif user_action.action_type == "open_short":  # sell PT to open short
            user_action.direction = "out"  # calcOutGivenIn
            user_action.token_out = "base"  # sell known PT for unknown base
            market_deltas, wallet_deltas = self.pricing_model.open_short(user_action)
        elif user_action.action_type == "close_short":  # buy PT to close short
            user_action.direction = "in"  # calcInGivenOut
            user_action.token_in = "base"  # buy known PT for unknown base
            market_deltas, wallet_deltas = self.pricing_model.close_short(user_action)
        else:
            raise ValueError(f'ERROR: Unknown trade type "{user_action["action_type"]}".')
        # update market state
        self.update_market(market_deltas)
        self.update_spot_price()
        # TODO: self.update_LP_pool(wallet_deltas["fees"])
        return wallet_deltas

    def get_market_state_string(self):
        """Returns a formatted string containing all of the Market class member variables"""
        strings = [f"{attribute} = {value}" for attribute, value in self.__dict__.items()]
        state_string = "\n".join(strings)
        return state_string

    def tick(self, delta_time):
        """Increments the time member variable"""
        self.time += delta_time

    def update_spot_price(self):
        """Update the spot price"""
        if self.pricing_model.model_name() == "Hyperdrive":
            self.spot_price = self.pricing_model.calc_spot_price(
                share_reserves=self.share_reserves,
                bond_reserves=self.bond_reserves,
                init_share_price=self.init_share_price,
                share_price=self.share_price,
                time_remaining=time_utils.stretch_time(self.token_duration, self.time_stretch_constant),
            )
        else:
            self.spot_price = np.nan
