"""Budget class for agents."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from fixedpointmath import FixedPoint, FixedPointMath
from numpy.random._generator import Generator as NumpyGenerator


@dataclass
class Budget:
    """Specifications for generating a random budget sample.

    This is used for assigning the agent's budget in base tokens.
    Wei in the variables below refers to the smallest unit of base, not to ETH.
    """

    mean_wei: int = FixedPoint(5_000).scaled_value
    std_wei: int = FixedPoint(2_000).scaled_value
    min_wei: int = FixedPoint(1_000).scaled_value
    max_wei: int = FixedPoint(10_000).scaled_value

    def sample_budget(self, rng: NumpyGenerator) -> FixedPoint:
        """Return a sample from a clipped normal distribution.

        Sample from normal distribution with mean of mean_wei and standard deviation of std_wei.
        Then clip to between a minimum of min_wei and a maximum of max_wei.

        Arguments
        ---------
        rng : NumpyGenerator
            The NumpyGenerator provides access to a wide range of distributions, and stores the random state.

        Returns
        -------
        FixedPoint
            A sample from a clipped random normal distribution according to the parameters defined at construction
        """
        return FixedPoint(
            scaled_value=FixedPointMath.clip(
                int(np.round(rng.normal(loc=self.mean_wei, scale=self.std_wei))),
                self.min_wei,
                self.max_wei,
            )
        )
