#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import common_setup
from common_setup import TopkExperiment
from common_setup import NumStatesDFCAParser
import top_k_parser

import os

from downward.reports.absolute import AbsoluteReport

from lab.environments import LocalEnvironment, BaselSlurmEnvironment

"""
Experiment script for top-k experiments
"""

DIR = os.path.dirname(os.path.abspath(__file__))
BENCHMARKS_DIR = os.environ["DOWNWARD_BENCHMARKS"]
PLANNER_DIR = os.environ["SYMBOLIC_TOP_K"]

MEMORY_LIMIT = 6144
CPU_MEMORY = 6354  # Infai_2 has 6354 MB per

DRIVER_OPTIONS = ["--overall-time-limit", "15m", "--overall-memory-limit", f"{MEMORY_LIMIT}M"]
NUM_PLANS = 1000


if common_setup.is_running_on_cluster():
    SUITE = common_setup.DEFAULT_OPTIMAL_SUITE + common_setup.OPTIMAL_SUITE_ADL
    NUM_PLANS = 10000
    ENVIRONMENT = BaselSlurmEnvironment(partition="infai_2", memory_per_cpu=f"{CPU_MEMORY}M")
else:
    # SUITE = common_setup.TopkExperiment.DEFAULT_TEST_SUITE
    SUITE = [
        "blocks:probBLOCKS-8-1.pddl", # probBLOCKS-<n>-<k>.pddl, where n = 4..17 and k = 0..2
        "gripper:prob01.pddl", # prob_<x>.pddl, where x = 01..20
        "sokoban-opt08-strips:p01.pddl", # p<x>.pddl, where x = 01..30
        "elevators-opt08-strips:p04.pddl",
    ]
    ENVIRONMENT = LocalEnvironment(processes=7)
    DRIVER_OPTIONS = ["--overall-time-limit", "100s"]

CONFIGS = []

# "symk_bd(plan_selection=top_k(num_plans=infinity,write_plans=true),cost_type=one,bound=15,simple=true)"
for nick, search_option in {
        "q=2_with_loops": f"symq_bd(quality=2,plan_selection=top_k(num_plans={NUM_PLANS}))",
        "q=2_simple":     f"symq_bd(quality=2,plan_selection=top_k(num_plans={NUM_PLANS}),simple=true)",
        "q=2_unit_cost":  f"symq_bd(quality=2,plan_selection=top_k(num_plans={NUM_PLANS}),cost_type=one)",
    }.items():
    CONFIGS += [
        common_setup.Config(
            nick,
            "master",
            ["--search", search_option],
            driver_options=DRIVER_OPTIONS,
        ),
    ]

exp = common_setup.TopkExperiment(
    repo_base=PLANNER_DIR,
    configs=CONFIGS,
    environment=ENVIRONMENT,
)
exp.add_resource("top_k_validator", os.path.join(DIR, "top_k_validator.sh"))

exp.add_suite(BENCHMARKS_DIR, SUITE)

exp.add_parser(exp.EXITCODE_PARSER)
exp.add_parser(exp.TRANSLATOR_PARSER)
exp.add_parser(exp.SINGLE_SEARCH_PARSER)
exp.add_parser(exp.PLANNER_PARSER)
exp.add_parser(top_k_parser.get_parser())
exp.add_parser(NumStatesDFCAParser())

ATTRIBUTES = TopkExperiment.DEFAULT_TABLE_ATTRIBUTES + [
    "plan_costs",
    "broken_plan_files",
    "failed_plans",
    "found_plans",
    "identical_plan_files",
]

exp.add_step("build", exp.build)
exp.add_step("start", exp.start_runs)
exp.add_step("construct_dfca", exp.construct_dfca)
exp.add_step("parse", exp.parse)
exp.add_fetcher(name="fetch")
exp.add_step("validate_plans", exp.validate_plans)
exp.add_report(
    AbsoluteReport(attributes=ATTRIBUTES, filter_algorithm=[x.nick for x in CONFIGS]),
    outfile="topk-report.html",
)
exp.add_step("create_k_coverage", exp.create_k_coverage_plot, NUM_PLANS)
exp.add_step("create_num_states_scatterplot", exp.create_num_states_scatterplot)

exp.run_steps()
