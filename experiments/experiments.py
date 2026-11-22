#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import common_setup
from common_setup import TopkExperiment
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
    ENVIRONMENT = BaselSlurmEnvironment(partition="infai_2", memory_per_cpu=f"{CPU_MEMORY}M")
else:
    # SUITE = common_setup.TopkExperiment.DEFAULT_TEST_SUITE
    SUITE = [
        "blocks:probBLOCKS-4-0.pddl", # probBLOCKS-<n>-<k>.pddl, where n = 4..17 and k = 0..2
        "gripper:prob01.pddl", # prob_<x>.pddl, where x = 01..20
        "sokoban-sat08-strips:p01.pddl", # p<x>.pddl, where x = 01..30
        "quantum-layout-sat23-strips:p01.pddl", # p<x>.pddl, where x = 01..20
    ]
    ENVIRONMENT = LocalEnvironment(processes=7)
    DRIVER_OPTIONS = ["--overall-time-limit", "100s"]

CONFIGS = []
for dir in ["bd"]:
    CONFIGS += [
        common_setup.Config(
            f"sym-{dir}",
            "master",
            ["--search", f"symq_{dir}(quality=1.0,plan_selection=top_k(num_plans={NUM_PLANS}))"],
            # mit unit-costs: symk verwenden
            # - networkx für visualisierung

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

ATTRIBUTES = TopkExperiment.DEFAULT_TABLE_ATTRIBUTES + [
    "plan_costs",
    "broken_plan_files",
    "failed_plans",
    "found_plans",
    "identical_plan_files",
]

exp.add_step("build", exp.build)
exp.add_step("start", exp.start_runs)
exp.add_step("parse", exp.parse)
exp.add_fetcher(name="fetch")
exp.add_step("validate_plans", exp.validate_plans)
exp.add_report(
    AbsoluteReport(attributes=ATTRIBUTES, filter_algorithm=[x.nick for x in CONFIGS]),
    outfile="topk-report.html",
)
exp.add_step("create_k_coverage", exp.create_k_coverage_plot, NUM_PLANS)

exp.run_steps()
