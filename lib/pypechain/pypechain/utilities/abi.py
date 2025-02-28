"""Utilities for solidity contract ABIs."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import List, NamedTuple, Sequence, TypeGuard, cast

from pypechain.utilities.format import capitalize_first_letter_only
from pypechain.utilities.types import solidity_to_python_type
from web3 import Web3
from web3.types import ABI, ABIElement, ABIEvent, ABIFunction, ABIFunctionComponents, ABIFunctionParams


class Input(NamedTuple):
    """An input of a function or event."""

    internalType: str
    name: str
    type: str
    indexed: bool | None = None


class Output(NamedTuple):
    """An output of a function or event."""

    internalType: str
    internalType: str
    name: str
    type: str


class AbiItem(NamedTuple):
    """An item of an ABI, can be an event, function or struct."""

    type: str
    inputs: List[Input]
    stateMutability: str | None = None
    anonymous: bool | None = None
    name: str | None = None
    outputs: List[Output] | None = None


class AbiJson(NamedTuple):
    """A JSON representation of a solidity contract's Application Boundary Interface."""

    abi: ABI


def load_abi(abi_path: str) -> AbiJson:
    """Loads the abi file into a json.

    Arguments
    ---------
    abi_path : str
        Where the abi json is location.

    Returns
    -------
    AbiJson
        A named tuple representation of an abi json file.
    """

    with open(abi_path, "r", encoding="utf-8") as abi_file:
        data = json.load(abi_file)

        # Assuming that the ABI data structure is at the top level of the JSON
        # (i.e., the file is a list of ABI items):
        abi_items = [cast(ABIElement, item) for item in data]

        return AbiJson(abi=abi_items)


def is_abi_function(item: ABIElement) -> TypeGuard[ABIFunction]:
    """Typeguard function for ABIFunction.

    Arguments
    ---------
    item:  Any
        The item we are confirming is an ABIFunction

    Returns
    -------
    TypeGuard[ABIFunction]
    """
    # Check if the required keys exist
    required_keys = ["type", "name", "inputs"]

    # Check if the required keys exist
    if not all(key in item for key in required_keys):
        return False

    # Check if the type is "function"
    if item.get("type") != "function":
        return False

    return True


def is_abi_event(item: ABIElement) -> TypeGuard[ABIEvent]:
    """Typeguard function for ABIEvent.

    Arguments
    ---------
    item:  Any
        The item we are confirming is an ABIFunction

    Returns
    -------
    TypeGuard[ABIEvent]
    """
    # Check if the required keys exist
    required_keys = ["type", "name", "inputs"]

    # Check if the required keys exist
    if not all(key in item for key in required_keys):
        return False

    # Check if the type is "event"
    if item.get("type") != "event":
        return False

    return True


@dataclass
class StructInfo:
    """Solidity struct information needed for codegen."""

    name: str
    values: list[StructValue]


@dataclass
class StructValue:
    """The name and python type of a solidity struct value."""

    name: str
    # TODO: type this better with an exahaustive list of python type strings.  Even better, maybe a
    # mapping from solidity to python types?
    solidity_type: str
    python_type: str


# This is a recursive function, need to initialize with an empty dict.
# pylint: disable=dangerous-default-value
def get_structs(
    function_params: Sequence[ABIFunctionParams] | Sequence[ABIFunctionComponents],
    structs: dict[str, StructInfo] = {},
) -> dict[str, StructInfo]:
    """Recursively gets all the structs for a contract by walking all function parameters.

     Pseudo code of the shape of a Sequence[ABIFunctionParams]:
     [
        { #ABIFunctionParams
            name:
            type: asdf
            internalType:
            components:
        },
        { #ABIFunctionParams
            name:
            type:
            internalType:
            components: [ #Sequence[ABIFunctionComponents]
                { #ABIFunctionComponents
                    name:
                    type:
                },
                { #ABIFunctionComponents
                    name:
                    type:
                    internalType:
                    components: # Sequence[ABIFunctionComponents]
                }
            ]
        },
    ]

    Arguments
    ---------
    file_path : Path
        the file path to the ABI.

    structs : dict[str, StructInfo]
        empty initialized return value.

    Returns
    -------
    List[Union[ABIFunction, ABIEvent]]
        _description_
    """

    for param in function_params:
        components = param.get("components")
        internal_type = cast(str, param.get("internalType", ""))

        # if we find a struct, we'll add it to the dict of StructInfo's
        if is_struct(internal_type) and components:
            struct_name = get_param_name(param)
            struct_values: list[StructValue] = []

            # walk over the components of the struct
            for component in components:
                component_internal_type = cast(str, component.get("internalType", ""))

                # do recursion if nested struct
                if is_struct(component_internal_type):
                    get_structs([component], structs)

                component_name = get_param_name(component)
                component_type = component_name if is_struct(component_internal_type) else component.get("type", "")
                python_type = solidity_to_python_type(component_type)
                struct_values.append(
                    StructValue(
                        name=component_name,
                        solidity_type=component_type,
                        python_type=python_type,
                    )
                )

            # lastly, add the struct to the dict
            structs[struct_name] = StructInfo(name=struct_name, values=struct_values)
    return structs


def get_structs_for_abi(abi: ABI) -> dict[str, StructInfo]:
    """

    Arguments
    ---------
    abi : ABI
        An Application Boundary Interface object.

    Returns
    -------
    dict[str, StructInfo]
        A dictionary of StructInfos keyed by name.
    """
    structs: dict[str, StructInfo] = {}
    for item in abi:
        if is_abi_function(item):
            fn_inputs = item.get("inputs")
            fn_outputs = item.get("outputs")
            if fn_inputs:
                input_structs = get_structs(fn_inputs)
                structs.update(input_structs)
            if fn_outputs:
                output_structs = get_structs(fn_outputs)
                structs.update(output_structs)

    return structs


def is_struct(internal_type: str) -> bool:
    """Returns True if the internal type of the parameter is a solidity struct.

    Arguments
    ---------
    internal_type : str
        The internalType attribute of an ABIFunctionParams or ABIFunctionComponents.  If the
        internal type has the form 'struct ContractName.StructName' then we know we are dealing with
        solidity struct.  Otherwise it will be equivalent to the 'type' attribute.

    Returns
    -------
    bool
        If the type is a struct.
    """
    # internal_type looks like 'struct ContractName.StructName' if they are structs
    return bool(internal_type.startswith("struct"))


def get_param_name(param_or_component: ABIFunctionParams | ABIFunctionComponents) -> str:
    """Returns the name for a given ABIFunctionParams or ABIFunctionComponents.

    If the item is a struct, then we pull the name from the internalType attribute, otherwise we use
    the name if available.

    Arguments
    ---------
    param : ABIFunctionParams | ABIFunctionComponents


    Returns
    -------
    str
        The name of the item.
    """
    internal_type = cast(str, param_or_component.get("internalType", ""))
    if is_struct(internal_type):
        # internal_type looks like 'struct ContractName.StructName' if it is a struct,
        # pluck off the name
        string_type = internal_type.split(".").pop()
        return capitalize_first_letter_only(string_type)

    return param_or_component.get("name", "")


def load_abi_from_file(file_path: Path) -> ABI:
    """Loads a contract ABI from a file.

    Arguments
    ---------
    file_path : Path
        The path to the ABI file.

    Returns
    -------
    Any
        An object containing the contract's abi.
    """

    with open(file_path, "r", encoding="utf-8") as file:
        json_file = json.load(file)
        return json_file["abi"] if "abi" in json_file else json_file


def get_abi_items(file_path: Path) -> list[ABIElement]:
    """Gets all the

    Arguments
    ---------
    file_path : Path
        the file path to the ABI.

    Returns
    -------
    List[Union[ABIFunction, ABIEvent]]
        _description_
    """

    web3 = Web3()
    abi = load_abi_from_file(file_path)
    contract = web3.eth.contract(abi=abi)

    # leverage the private list of ABIFunction's
    # pylint: disable=protected-access
    abi_functions_and_events = contract.functions._functions
    return abi_functions_and_events
