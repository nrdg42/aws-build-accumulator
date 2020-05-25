#!/usr/bin/env python3
#
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License").
# You may not use this file except in compliance with the License.
# A copy of the License is located at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# or in the "license" file accompanying this file. This file is distributed
# on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either
# express or implied. See the License for the specific language governing
# permissions and limitations under the License.


import argparse
import json
import re

from ninja.misc import ninja_syntax


_ci_stages = [
    "build", "test", "report",
]


def get_add_job_args():
    return {
        "describing the build graph": [{
            "flags": ["-i", "--inputs"],
            "required": True,
            "nargs": "+",
            "metavar": "F",
            "help": "list of files that this job depends on",
        }, {
            "flags": ["-c", "--command"],
            "metavar": "C",
            "required": True,
            "help": "the command to run once all dependencies are satisfied",
        }, {
            "flags": ["-o", "--outputs"],
            "required": True,
            "metavar": "F",
            "nargs": "+",
            "help": "list of files that this job generates",
        }],
        "job control": [{
            "flags": ["-p", "--pipeline-name"],
            "required": True,
            "metavar": "P",
            "help": "which pipeline this job is a member of",
        }, {
            "flags": ["-s", "--ci-stage"],
            "required": True,
            "metavar": "S",
            "choices": _ci_stages,
            "help": "which CI stage this job should execute in. "
                    "Must be one of {%(choices)s}.",
        }, {
            "flags": ["--timeout"],
            "metavar": "N",
            "type": int,
            "help": "max number of seconds this job should run for"
        }, {
            "flags": ["--timeout-ok"],
            "action": "store_true",
            "help": "if the job times out, terminate it and return success"
        }, {
            "flags": ["--ok-returns"],
            "metavar": "RC",
            "nargs": "+",
            "help": "if the job exits with one of the listed return codes, "
                    "return success"
        }],
        "misc": [{
            "flags": ["--description"],
            "metavar": "DESC",
            "help": "string to print when this job is being run",
        }, {
            "flags": ["-v", "--verbose"],
            "action": "store_true",
            "help": "verbose output",
        }, {
            "flags": ["-w", "--very-verbose"],
            "action": "store_true",
            "help": "very verbose output",
        }],
    }


def add_job(args):
    try:
        with open("/tmp/litani_cache.json") as handle:
            cache = json.load(handle)
    except FileNotFoundError:
        cache = {
            "jobs": []
        }
    entry = {
        "inputs": args.inputs,
        "outputs": args.outputs,
        "command": args.command,
    }
    cache["jobs"].append(entry)
    if args.description:
        entry["description"] = args.description

    with open("/tmp/litani_cache.json", "w") as handle:
        json.dump(cache, handle, indent=2)


def to_rule_name(string):
    allowed = re.compile(r"[a-zA-Z0-9_]")
    return "".join([i for i in string if allowed.match(i)])


def run_build(_):
    with open("/tmp/litani_cache.json") as handle:
        cache = json.load(handle)

    rules = []
    builds = []
    for entry in cache["jobs"]:
        for required in ["inputs", "outputs", "command"]:
            if required not in entry:
                print(entry)
                exit(1)

        if "description" in entry:
            description = entry["description"]
        else:
            description = f"Running '{entry['command']}...'"
        rule_name = to_rule_name(entry["command"])
        rules.append({
            "name": rule_name,
            "description": description,
            "command": entry["command"],
        })

        builds.append({
            "inputs": entry["inputs"],
            "outputs": entry["outputs"],
            "rule": rule_name
        })

    with open("litani.ninja", "w") as handle:
        ninja = ninja_syntax.Writer(handle, width=70)
        for rule in rules:
            ninja.rule(**rule)
        for build in builds:
            ninja.build(**build)


def get_args():
    description = "Incrementally build up a dependency graph of jobs to execute"

    pars = argparse.ArgumentParser(description=description)
    subs = pars.add_subparsers(
        title="subcommands", dest="subcommand")
    subs.required = True

    run_build_pars = subs.add_parser("run-build")
    run_build_pars.set_defaults(func=run_build)
    for arg in []:
        flags = arg.pop("flags")
        run_build_pars.add_argument(*flags, **arg)

    add_job_pars = subs.add_parser("add-job")
    add_job_pars.set_defaults(func=add_job)
    for group_name, args in get_add_job_args().items():
        group = add_job_pars.add_argument_group(title=group_name)
        for arg in args:
            flags = arg.pop("flags")
            group.add_argument(*flags, **arg)

    return pars.parse_args()


def main():
    args = get_args()
    args.func(args)


if __name__ == "__main__":
    main()
