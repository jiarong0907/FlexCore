

class FlexCore:
    def __init__(self, planner, out_path):
        self.planner = planner
        self.input_builder = planner.inbuilder
        self.out_path = out_path

    def compute_plan(self):
        rdg_o, rdg_n = self.input_builder.build()
        self.planner.reconfig(rdg_o, rdg_n, self.out_path)