

class FlexCore:
    def __init__(self, planner, out_path, enable_action_ptr=False):
        self.planner = planner
        self.input_builder = planner.inbuilder
        self.out_path = out_path
        if self.input_builder.__class__.__name__ == 'JsonInputBuilder' \
                and self.planner.__class__.__name__ == 'ProgPlanner':
            self.input_builder.set_enable_action_ptr(enable_action_ptr)
            self.planner.set_enable_action_ptr(enable_action_ptr)

    def compute_plan(self):
        rdg_o, rdg_n = self.input_builder.build()
        self.planner.reconfig(rdg_o, rdg_n, self.out_path)