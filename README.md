# How to run
Requrements:
Python and the [uv package manager](https://docs.astral.sh/uv/).

## Run Sanity Checks on Randomized Languages
```uv run dfca.py randomized```
## Generate DFCA from command-line arguments
```uv run dfca.py from-arg a ab ababb bbab babba```
## Generate DFCA from a directory filled with plan files
We assume the convention that the Fast Downward planner uses,
meaning each plan is stored in a text-file `sas_plan.<n>` where `<n>` is a number.

```uv run dfca.py from-directory <path-to-plans>```

# A note on flags
To generate some possibly useful (or overly verbose) output to stdout, one can use the flag `-V` after `dfca.py` and to visualize the automaton after generation, one can use the flag `-v` in the same place.

The visualize flag is not recommended to be used with subcommand `randomized`.