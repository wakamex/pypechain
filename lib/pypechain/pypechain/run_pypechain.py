"""Script to generate typed web3.py classes for solidity contracts."""
from __future__ import annotations

import os
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Literal

from jinja2 import Template
from web3.types import ABIFunction

from pypechain.utilities.abi import (
    get_abi_items,
    get_param_name,
    get_structs_for_abi,
    is_abi_function,
    load_abi_from_file,
)
from pypechain.utilities.format import avoid_python_keywords, capitalize_first_letter_only
from pypechain.utilities.templates import setup_templates
from pypechain.utilities.types import solidity_to_python_type

NUMBER_OF_ARGS = 2

def main(abi_file_path: str, output_dir: str) -> None:
    """Generate class files for a given abi.

    Arguments
    ---------
    abi_file_path : str
        Path to the abi json file.
    output_dir: str
        Path to the directory to output the generated files.
    """
    # get names
    file_path = Path(abi_file_path)
    filename = file_path.name
    contract_name = os.path.splitext(filename)[0]

    # grab the templates
    contract_template, types_template = setup_templates()

    # render the code
    rendered_contract_code = render_contract_file(contract_name, contract_template, file_path)
    rendered_types_code = render_types_file(contract_name, types_template, file_path)

    # TODO: Add more features:
    # TODO:  events

    # Write the renders to a file
    types_output_file_path = Path(output_dir).joinpath(f"{contract_name}Types.py")
    contract_output_file_path = Path(output_dir).joinpath(f"{contract_name}Contract.py")
    # Make folder if it doesn't exist
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    with open(contract_output_file_path, "w", encoding="utf-8") as output_file:
        output_file.write(rendered_contract_code)
    with open(types_output_file_path, "w", encoding="utf-8") as output_file:
        output_file.write(rendered_types_code)


def render_contract_file(contract_name: str, contract_template: Template, abi_file_path: Path) -> str:
    """Return a string of the contract file to be generated.

    Arguments
    ---------
    contract_name : str
        The name of the contract.
    contract_template : Template
        A jinja template containging types for all structs within an abi.
    abi_file_path : Path
        The path to the abi file to parse.

    Returns
    -------
    str
        A serialized python file.
    """
    # TODO:  return types to function calls
    # Extract function names and their input parameters from the ABI
    abi_functions_and_events = get_abi_items(abi_file_path)

    function_datas = []
    for abi_function in abi_functions_and_events:
        if is_abi_function(abi_function):
            # TODO: investigate better typing here?  templete.render expects an object so we'll have to convert.
            name = abi_function.get("name", "")
            function_data = {
                # TODO: pass a typeguarded ABIFunction that has only required fields?
                # name is required in the typeguard.  Should be safe to default to empty string.
                "name": name,
                "capitalized_name": capitalize_first_letter_only(name),
                "input_names_and_types": get(abi_function, "inputs", include_types=True),
                "input_names": get(abi_function, "inputs", include_types=False),
                "outputs": get(abi_function, "outputs", include_types=True),
            }
            function_datas.append(function_data)
    # Render the template
    return contract_template.render(contract_name=contract_name, functions=function_datas)


def render_types_file(contract_name: str, types_template: Template, abi_file_path: Path) -> str:
    """Return a string of the types file to be generated.

    Arguments
    ---------
    contract_name : str
        The name of the contract.
    types_template : Template
        A jinja template containging types for all structs within an abi.
    abi_file_path : Path
        The path to the abi file to parse.

    Returns
    -------
    str
        A serialized python file.
    """
    abi = load_abi_from_file(abi_file_path)
    structs_by_name = get_structs_for_abi(abi)
    structs_list = list(structs_by_name.values())
    structs = [asdict(struct) for struct in structs_list]
    return types_template.render(contract_name=contract_name, structs=structs)


def get(
    function: ABIFunction, param_type: Literal["inputs", "outputs"], include_types: bool = True
) -> list[str] | dict[str, str]:
    # TODO: recursively handle empty strings for evil nested tuples with no names.
    """Return function inputs or outputs, optionally including types.

    Arguments
    ---------
    function : ABIFunction
        The function to parse.
    param_type : str
        Choice of "inputs" or "outputs"
    include_types : bool
        Whether to include the types of the parameters. Defaults to True.

    list[str] | dict[str, str]
        The parsed parameters, in a list without types, or a dict with types.
    """
    parameters = function.get(param_type, [])
    params = {}
    anon_count = 0
    for param in parameters:
        name = get_param_name(param)
        if name is None or name == "":
            name = f"{param_type[:-1]}{anon_count}"
            param["name"] = name
            anon_count += 1
        params[avoid_python_keywords(name)] = solidity_to_python_type(param.get("type", "unknown"))
    return [f"{k}: {v}" for k, v in params.items()] if include_types else list(params.keys())


if __name__ == "__main__":
    if len(sys.argv) != NUMBER_OF_ARGS:
        print("Usage: python script_name.py <path_to_abi_file> <output_dir>")
    else:
        # TODO: add a bash script to make this easier, i.e. ./pypechain './abis', './build'
        # TODO: make this installable so that other packages can use the command line tool
        main(sys.argv[1], sys.argv[2])
