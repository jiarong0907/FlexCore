import os

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

def one_run(inbuilder_choice, input, planner_choice, enable_action_ptr):
    input_builder_cls = input_builder_choice_mapping[inbuilder_choice]
    path_prefex = os.path.join("..", "examples", input, input)
    path_old = None
    path_new = None
    if inbuilder_choice == "json":
        path_old = path_prefex+"_old.json"
        path_new = path_prefex+"_new.json"
    elif inbuilder_choice == "graph":
        path_old = path_prefex+"_old.txt"
        path_new = path_prefex+"_new.txt"
    elif inbuilder_choice == "obj":
        path_old = path_prefex+"_old.graph"
        path_new = path_prefex+"_new.graph"

    input_builder = input_builder_cls(path_old, path_new)

    planner_cls = planner_choice_mapping[planner_choice]
    planner = planner_cls(input_builder)

    out_path = os.path.join("..", "examples", input)
    flexcore = FlexCore(planner, out_path, enable_action_ptr)
    flexcore.compute_plan()


def main() -> None:
    """The main program"""

    json_input = ["consistency_example", "multi_tenant", "normalization"]
    required_action_ptr = ["action_ptr", "action_ptr2", "no2hit", "switch2switch"]
    graph_input = ["test1", "test2", "test3", "test4", "test5", "test6"]
    obj_input = ["synthesized_test1"]

    for input in json_input:
        for planner_choice in planner_choice_mapping.keys():
            one_run("json", input, planner_choice, False)

    for input in required_action_ptr:
        one_run("json", input, "prog", True)

    for input in graph_input:
        for planner_choice in planner_choice_mapping.keys():
            one_run("graph", input, planner_choice, False)

    for input in obj_input:
        for planner_choice in planner_choice_mapping.keys():
            one_run("obj", input, planner_choice, False)


if __name__ == "__main__":
    main()
