# Install -- overview

Elf-simulations is currently supported only for Python 3.10.

### 1. Install Pyenv

Follow [Pyenv install instructions](https://github.com/pyenv/pyenv#installation).

### 2. Clone Elf-simulations repo

Clone the repo into a <repo_location> of your choice.

```bash
git clone https://github.com/delvtech/elf-simulations.git <repo_location>
```

### 3. Set up virtual environment

Here we use [venv](https://docs.python.org/3/library/venv.html) which is part of the built-in standard Python library, but any virtual environment package is fine.

```bash
cd <repo_location>
pyenv install 3.10
pyenv local 3.10
python -m venv .venv
source .venv/bin/activate
```

### 4. Install Elf-simulations

```bash
python -m pip install --upgrade pip
python -m pip install --upgrade -r requirements.txt
```

Each package within `lib` has its own dependencies.
If you want to run the CI (tests, linting, type checking) or improve the documentation, then you must also install the dev packages:

```bash
python -m pip install --upgrade -r requirements-dev.txt
```

An explanation of what the above steps do:

- `pyenv install 3.10` You should now see the correct version when you run `pyenv versions`.
- `pyenv local 3.10` This command creates a `.python-version` file in your current directory. If you have pyenv active in your environment, this file will automatically activate this version for you.
- `python -m venv .venv` This will create a `.venv` folder in your repo directory that stores the local python build & packages. After this command you should be able to type which python and see that it points to an executable inside `.venv/`.
- `python -m pip install --upgrade -r requirements.txt` This installs elfpy locally such that the install updates automatically any time you change the source code. This also installs all dependencies defined in `pyproject.toml`.

Finally, you can test that everything is working by calling: `python -m pytest .`

## Working with smart contracts (optional)

We run tests and offer utilities that depend on executing bytecode compiled from Hyperdrive solidity contracts. This is not required to use elfpy.

NOTE: The Hyperdrive solidity implementation is currently under security review, and thus is not available publicly.
The following instructions will not work for anyone who is not a member of Delv.

### 1. Set up smart contracts

Clone the hyperdrive repo, then create a [sym link](https://en.wikipedia.org/wiki/Symbolic_link#POSIX_and_Unix-like_operating_systems) at `hyperdrive_solidity/` pointing to the repo location.

```bash
git clone git@github.com:delvtech/hyperdrive.git ../hyperdrive
ln -s ../hyperdrive hyperdrive_solidity
```

### 2. Install Hyperdrive

Complete the steps in Hyperdrive's [Pre-requisites](https://github.com/delvtech/hyperdrive#pre-requisites) and [Build](https://github.com/delvtech/hyperdrive#build) sections.

## Notes

The default installation directions above should automatically install all local sub-packages, and should be sufficient for development.

We also support installing each subpackage independently. For example:
```
python -m pip install --upgrade lib/agent0[with-dependencies]
```
Internally, the above installation calls
```
pip install agent0[base] # Install with base packages only (this is what's called in requirements.txt)
pip install agent0[lateral] # Installs dependent sub-packages from git (e.g., ethpy)
```

You can test against a local testnet node using [Anvil](<[url](https://book.getfoundry.sh/reference/anvil/)>) with `anvil`.

We use [Docker](docs.docker.com/get-docker) for building images.
