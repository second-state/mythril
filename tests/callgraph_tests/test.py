import os
import unittest

from mythril.support.callgraph import Callgraph

class TestCallGraph(unittest.TestCase):
    # TODO Refactor: Make it more compatible with other Mythril tests
    def __init__(self, *args, **kwargs):
        super(TestCallGraph, self).__init__(*args, **kwargs)
        self.path = os.path.join(os.getcwd(), "tests/callgraph_tests")
        self.contract_path = os.path.join(self.path, "input_contracts")
        self.output_path = os.path.join(self.path, "outputs_current")
        self.input_path = os.path.join(self.path, "inputs")

    def execute_contract_tests(self, contract):
        contract_file_path = os.path.join(self.contract_path, contract)
        callgraph = Callgraph()
        callgraph.import_solidity_file(contract_file_path)

        name = contract.split(".")[0]
        input_file_path = os.path.join(self.input_path, "%s.in"%name)
        output_file_path = os.path.join(self.output_path, "%s.out"%name)
        with open(input_file_path, 'r') as input_file,\
            open(output_file_path, 'w') as output_file:
            for line in input_file:
                split = line.split()
                dependencies = sorted(list(callgraph.request_call_dependency(split)))
                output_file.write(",".join(dependencies))
                output_file.write("\n")

    def test_callgraph(self):
        # TODO Check execution results automatically.
        contracts = filter(lambda x: not x.startswith("."),\
                        next(os.walk(self.contract_path))[2])
        for contract in contracts:
            self.execute_contract_tests(contract)

if __name__ == '__main__':
    unittest.main()
