import argparse

from flexcore import FlexCore
from exec_planner import ExecPlanner
from elem_planner import ElemPlanner
from prog_planner import ProgPlanner
from input_builder import GraphInputBuilder, JsonInputBuilder, ObjInputBuilder

planner_choice_mapping = {
    "exec": ExecPlanner,
    "elem": ElemPlanner,
    "prog": ProgPlanner,
}

input_builder_choice_mapping = {
    "graph": GraphInputBuilder,
    "json": JsonInputBuilder,
    "obj": ObjInputBuilder,
}

def _configure() -> argparse.Namespace:
    """Sets up arg parser"""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-p",
        dest="planner",
        choices=["exec", "elem", "prog"],
        required=True,
        default="prog",
        help="The choice of planner",
    )
    parser.add_argument(
        "-b",
        dest="inbuilder",
        choices=["graph", "json", "obj"],
        required=True,
        default="json",
        help="The choice of input builder",
    )
    parser.add_argument(
        "-old",
        dest="old_path",
        required=True,
        help="The path of the old json/graph/obj",
    )
    parser.add_argument(
        "-new",
        dest="new_path",
        required=True,
        help="The path of the new json/graph/obj",
    )
    parser.add_argument(
        "-out",
        dest="out_path",
        required=True,
        help="The path to save generated commands",
    )
    parser.add_argument(
        "-use_action_ptr",
        dest="enable_action_ptr",
        action='store_true',
        default=False,
        help="Enable action pointer for program consistency or not",
    )
    return parser.parse_args()

def main(args: argparse.Namespace) -> None:
    """The main program"""

    input_builder_cls = input_builder_choice_mapping[args.inbuilder]
    input_builder = input_builder_cls(args.old_path, args.new_path)

    planner_cls = planner_choice_mapping[args.planner]
    planner = planner_cls(input_builder)

    flexcore = FlexCore(planner, args.out_path, args.enable_action_ptr)
    flexcore.compute_plan()


if __name__ == "__main__":
    main(_configure())
