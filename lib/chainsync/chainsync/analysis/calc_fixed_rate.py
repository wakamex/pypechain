"""Calculate the fixed interest rate."""
from decimal import Decimal

import numpy as np
import pandas as pd

from .calc_spot_price import calc_spot_price

def calc_fixed_rate(spot_price: pd.Series, position_duration: Decimal):
    """Calculate fixed rate from spot price."""
    # Position duration (in seconds) in terms of fraction of year
    annualized_time = float(position_duration / Decimal(60 * 60 * 24 * 365))
    return (1 - spot_price) / (spot_price * annualized_time)

def calc_fixed_rate_df(trade_data, config_data):
    """Calculate fixed rate from trade and config data."""
    trade_data["rate"] = np.nan
    annualized_time = config_data["positionDuration"] / Decimal(60 * 60 * 24 * 365)
    spot_price = calc_spot_price(
        trade_data["share_reserves"],
        trade_data["bond_reserves"],
        config_data["initialSharePrice"],
        config_data["invTimeStretch"],
    )
    fixed_rate = (Decimal(1) - spot_price) / (spot_price * annualized_time)
    x_data = trade_data["timestamp"]
    y_data = fixed_rate
    return x_data, y_data
