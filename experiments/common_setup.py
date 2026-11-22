# -*- coding: utf-8 -*-

import json
import os
import platform
import sys
import re

from lab.experiment import ARGPARSER
from lab import tools

import matplotlib.pyplot as plt

from downward.experiment import FastDownwardRun, FastDownwardExperiment


def parse_args():
    ARGPARSER.add_argument(
        "--test",
        choices=["yes", "no", "auto"],
        default="auto",
        dest="test_run",
        help="test experiment locally on a small suite if --test=yes or "
        "--test=auto and we are not on a cluster",
    )
    return ARGPARSER.parse_args()


ARGS = parse_args()


DEFAULT_OPTIMAL_SUITE = [
    "agricola-opt18-strips",
    "airport",
    "barman-opt11-strips",
    "barman-opt14-strips",
    "blocks",
    "childsnack-opt14-strips",
    "data-network-opt18-strips",
    "depot",
    "driverlog",
    "elevators-opt08-strips",
    "elevators-opt11-strips",
    "floortile-opt11-strips",
    "floortile-opt14-strips",
    "freecell",
    "ged-opt14-strips",
    "grid",
    "gripper",
    "hiking-opt14-strips",
    "logistics00",
    "logistics98",
    "miconic",
    "movie",
    "mprime",
    "mystery",
    "nomystery-opt11-strips",
    "openstacks-opt08-strips",
    "openstacks-opt11-strips",
    "openstacks-opt14-strips",
    "openstacks-strips",
    "organic-synthesis-opt18-strips",
    "organic-synthesis-split-opt18-strips",
    "parcprinter-08-strips",
    "parcprinter-opt11-strips",
    "parking-opt11-strips",
    "parking-opt14-strips",
    "pathways",
    "pegsol-08-strips",
    "pegsol-opt11-strips",
    "petri-net-alignment-opt18-strips",
    "pipesworld-notankage",
    "pipesworld-tankage",
    "psr-small",
    "quantum-layout-opt23-strips",
    "rovers",
    "satellite",
    "scanalyzer-08-strips",
    "scanalyzer-opt11-strips",
    "snake-opt18-strips",
    "sokoban-opt08-strips",
    "sokoban-opt11-strips",
    "spider-opt18-strips",
    "storage",
    "termes-opt18-strips",
    "tetris-opt14-strips",
    "tidybot-opt11-strips",
    "tidybot-opt14-strips",
    "tpp",
    "transport-opt08-strips",
    "transport-opt11-strips",
    "transport-opt14-strips",
    "trucks-strips",
    "visitall-opt11-strips",
    "visitall-opt14-strips",
    "woodworking-opt08-strips",
    "woodworking-opt11-strips",
    "zenotravel",
]

OPTIMAL_SUITE_ADL = [
    "assembly",
    "caldera-opt18-adl",
    "caldera-split-opt18-adl",
    "cavediving-14-adl",
    "citycar-opt14-adl",
    "folding-opt23-adl",
    "labyrinth-opt23-adl",
    "maintenance-opt14-adl",
    "miconic-fulladl",
    "miconic-simpleadl",
    "nurikabe-opt18-adl",
    "openstacks",
    "openstacks-opt08-adl",
    "optical-telegraphs",
    "philosophers",
    "psr-large",
    "psr-middle",
    "recharging-robots-opt23-adl",
    "ricochet-robots-opt23-adl",
    "rubiks-cube-opt23-adl",
    "schedule",
    "settlers-opt18-adl",
    "slitherlink-opt23-adl",
    "trucks",
]


DEFAULT_SATISFICING_SUITE = [
]

ALL_SUITE = [
]


def get_script():
    """Get file name of main script."""
    return tools.get_script_path()


def get_script_dir():
    """Get directory of main script.

    Usually a relative directory (depends on how it was called by the user.)"""
    return os.path.dirname(get_script())


def get_experiment_name():
    """Get name for experiment.

    Derived from the absolute filename of the main script, e.g.
    "/ham/spam/eggs.py" => "spam-eggs"."""
    script = os.path.abspath(get_script())
    script_dir = os.path.basename(os.path.dirname(script))
    script_base = os.path.splitext(os.path.basename(script))[0]
    return "%s-%s" % (script_dir, script_base)


def get_data_dir():
    """Get data dir for the experiment.

    This is the subdirectory "data" of the directory containing
    the main script."""
    return os.path.join(get_script_dir(), "data", get_experiment_name())


def get_repo_base():
    """Get base directory of the repository, as an absolute path.

    Search upwards in the directory tree from the main script until a
    directory with a subdirectory named ".git" is found.

    Abort if the repo base cannot be found."""
    path = os.path.abspath(get_script_dir())
    while os.path.dirname(path) != path:
        if os.path.exists(os.path.join(path, ".git")):
            return path
        path = os.path.dirname(path)
    sys.exit("repo base could not be found")


def is_running_on_cluster():
    return re.fullmatch(r"login12|ic[ab]\d\d", platform.node())


def is_test_run():
    return ARGS.test_run == "yes" or (
        ARGS.test_run == "auto" and not is_running_on_cluster()
    )


def get_algo_nick(config_nick):
    return config_nick


class Config(object):
    """Hold information about a planner configuration.

    See FastDownwardExperiment.add_algorithm() for documentation of the
    constructor's options.

    """

    def __init__(
        self, nick, branch, component_options, build_options=None, driver_options=None
    ):
        self.nick = nick
        self.branch = branch
        self.component_options = component_options
        self.build_options = build_options
        self.driver_options = driver_options


class TopkExperiment(FastDownwardExperiment):
    """Subclass of FastDownwardExperiment with some convenience features."""

    DEFAULT_TEST_SUITE = [
        "depot:p01.pddl",
        "gripper:prob01.pddl",
        "ged-opt14-strips:d-1-2.pddl",
        "transport-opt14-strips:p05.pddl",
    ]

    DEFAULT_TABLE_ATTRIBUTES = [
        "cost",
        "coverage",
        "error",
        "evaluations",
        "expansions",
        "expansions_until_last_jump",
        "generated",
        "memory",
        "planner_memory",
        "planner_time",
        "quality",
        "run_dir",
        "score_evaluations",
        "score_expansions",
        "score_generated",
        "score_memory",
        "score_search_time",
        "score_total_time",
        "search_time",
        "total_time",
    ]

    DEFAULT_SCATTER_PLOT_ATTRIBUTES = [
        "evaluations",
        "expansions",
        "expansions_until_last_jump",
        "initial_h_value",
        "memory",
        "search_time",
        "total_time",
    ]

    PORTFOLIO_ATTRIBUTES = [
        "cost",
        "coverage",
        "error",
        "plan_length",
        "run_dir",
    ]

    def __init__(self, repo_base=None, configs=None, path=None, **kwargs):
        if repo_base is None:
            repo_base = get_repo_base()

        path = path or get_data_dir()

        FastDownwardExperiment.__init__(self, path=path, **kwargs)

        for config in configs:
            self.add_algorithm(
                get_algo_nick(config.nick),
                repo_base,
                config.branch,
                config.component_options,
                build_options=config.build_options,
                driver_options=config.driver_options,
            )
            self._algorithms[get_algo_nick(config.nick)].driver_options.remove(
                "--validate"
            )
        self._configs = configs

    # We overwrite this function to add additional commands
    def _add_runs(self):
        tasks = self._get_tasks()
        for algo in self._algorithms.values():
            for task in tasks:
                fd_run = FastDownwardRun(self, algo, task)
                fd_run.add_command(
                    "plan_list",
                    ["{top_k_validator}", "{domain}", "{problem}", "found_plans/"],
                )
                # fd_run.add_command(
                #     "zip_plans", ["zip", "-r", "found_plans.zip", "found_plans/"]
                # )
                # fd_run.add_command("rm_plans", ["rm", "-r", "found_plans/"])
                self.add_run(fd_run)

    @classmethod
    def _is_portfolio(cls, config_nick):
        return "fdss" in config_nick

    @classmethod
    def get_supported_attributes(cls, config_nick, attributes):
        if cls._is_portfolio(config_nick):
            return [attr for attr in attributes if attr in cls.PORTFOLIO_ATTRIBUTES]
        return attributes

    def validate_plans(self):
        issues = False
        assert os.path.exists(os.path.join(self.eval_dir, "properties"))
        with open(os.path.join(self.eval_dir, "properties"), "r") as f:
            props = json.load(f)
        for i, key in enumerate(props):
            cur_data = props[key]
            if cur_data["broken_plan_files"] > 0:
                print(f"{key}: has {cur_data['broken_plan_files']} broken plan!")
                issues = True
            if cur_data["failed_plans"] > 0:
                print(f"{key}: has {cur_data['failed_plans']} failed plan!")
                issues = True

            # We compare all runs with each other
            for j, key2 in enumerate(props):
                if i >= j:
                    continue
                cur_data2 = props[key2]
                valid = plan_check(cur_data, cur_data2)
                if not valid:
                    print(f"{key} and {key2} have conflicting plan costs!")
                    issues = True

        if not issues:
            print("Everything fine :)!")

    def create_k_coverage_plot(
        self, num_requested_plans, filter_algorithm=None, outfile="k_coverage.png"
    ):
        assert os.path.exists(os.path.join(self.eval_dir, "properties"))
        with open(os.path.join(self.eval_dir, "properties"), "r") as f:
            props = json.load(f)
        config_to_k_coverage = dict()
        for key in props:
            cur_data = props[key]
            if filter_algorithm is None or cur_data["algorithm"] in filter_algorithm:
                if cur_data["algorithm"] not in config_to_k_coverage:
                    config_to_k_coverage[cur_data["algorithm"]] = [
                        0 for i in range(num_requested_plans)
                    ]
                for k in range(num_requested_plans):
                    if get_k_coverage(cur_data, k + 1):
                        config_to_k_coverage[cur_data["algorithm"]][k] += 1
                    else:
                        break

        fig, ax = plt.subplots()
        # ax.margins(0.05) # Optional, just adds 5% padding to the autoscaling
        ax.set_xlabel("number of requested loopless plans ($k$)")
        ax.set_ylabel("$k$-coverage")
        ax.set_xlim(1, num_requested_plans)
        ax.set_xscale("log")

        x_points = list(range(1, num_requested_plans + 1))
        for config in config_to_k_coverage:
            assert config_to_k_coverage[config] == sorted(
                config_to_k_coverage[config], reverse=True
            )
            plt.plot(x_points, config_to_k_coverage[config], label=config, linewidth=2)
        plt.legend()
        fig.savefig(os.path.join(self.eval_dir, "k_coverage.png"))


def get_k_coverage(run, num_requested_plans):
    if run["found_plans"] >= num_requested_plans:
        return True
    else:
        return run["coverage"] == 1


def plan_check(run1, run2):
    if run1["domain"] != run2["domain"] or run1["problem"] != run2["problem"]:
        return True

    if run1["found_plans"] >= run2["found_plans"]:
        primary = run1
        secondary = run2
    else:
        primary = run2
        secondary = run1

    primary_costs = sorted([int(x) for x in primary["plan_costs"].keys()])
    secondary_costs = sorted([int(x) for x in secondary["plan_costs"].keys()])

    if len(primary_costs) < len(secondary_costs):
        return False

    for i in range(len(secondary_costs)):
        if secondary_costs[i] != primary_costs[i]:
            return False

    for i in range(len(secondary_costs) - 1):
        cur_cost = str(secondary_costs[i])
        if secondary["plan_costs"][cur_cost] != primary["plan_costs"][cur_cost]:
            return False

    return True
