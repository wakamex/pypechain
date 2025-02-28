"""Information for creating an agent"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Type

from agent0.base.policies import BasePolicy
from fixedpointmath import FixedPoint

from .budget import Budget


@dataclass
class AgentConfig:
    """Information about an agent

    Attributes
    ----------
    policy : str
        The agent's policy; should match the class name
    name : str
        The name of the agent
    base_budget_wei : Budget | int
        The base token budget for the agent in units of wei
    eth_budget_wei : Budget | int
        The ethereum budget for the agent in units of wei
    number_of_agents : int
        The number of agents of this type to spin up
    private_keys : list[str] | None
        list of strings, where each key contains
    init_kwargs : dict
        A dictionary of keyword arguments for the policy constructor
    """

    # lots of configs!
    # pylint: disable=too-many-instance-attributes

    policy: Type[BasePolicy]
    name: str = "BoringBotty"
    base_budget_wei: Budget | int = Budget()
    eth_budget_wei: Budget | int = Budget(min_wei=int(1e18), max_wei=int(1e18))
    slippage_tolerance: FixedPoint | None = None # FixedPoint(0.0001)=0.01%
    number_of_agents: int = 1
    private_keys: list[str] | None = None
    init_kwargs: dict = field(default_factory=dict)

    def __post_init__(self):
        if self.private_keys is not None and len(self.private_keys) != self.number_of_agents:
            raise ValueError(
                f"if private_keys is set then {len(self.private_keys)=} must equal {self.number_of_agents=}"
            )
