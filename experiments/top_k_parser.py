#! /usr/bin/env python

import re

from lab.parser import Parser


class TopKParser(Parser):
    pass


def top_k_coverage(content, props):
    props["plan_costs"] = None
    props["found_plans"] = 0
    props["failed_plans"] = 0
    if "Plan costs:" not in content:
        return

    pattern = re.compile(r"Plan costs: (.+)\n", flags=re.M)
    assert len(re.findall(pattern, content)) == 1
    costs = [int(num) for num in re.findall(pattern, content)[0][1:-1].split()]
    props["plan_costs"] = dict()

    for plan_cost in costs:
        if plan_cost not in props["plan_costs"]:
            props["plan_costs"][plan_cost] = 0
        props["plan_costs"][plan_cost] += 1
        props["found_plans"] += 1
        if plan_cost == -1:
            props["failed_plans"] += 1


def get_parser():
    parser = TopKParser()
    parser.add_function(top_k_coverage)
    parser.add_pattern("broken_plan_files", r"Number of broken plans: (.+)", type=int)
    parser.add_pattern(
        "identical_plan_files", r"Number of identical plans: (.+)", type=int
    )
    return parser
