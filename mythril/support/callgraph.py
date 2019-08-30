from copy import deepcopy
from collections import defaultdict
from subprocess import PIPE, Popen

from mythril.exceptions import CompilerError

class Callgraph(object):
    def __init__(self):
        self._nodes = None
        self._edges = None

    @staticmethod
    def _get_callgraph_from_solidity_file(
        file_path: str, solc_binary: str = "solc", solc_args: str = None
    ):
        if ":" in file_path:
            file_path = file_path.split(":")[0]
        cmd = [solc_binary, "--callgraph", file_path]
        if solc_args:
            cmd.extend(solc_args.split())

        try:
            p = Popen(cmd, stdout=PIPE, stderr=PIPE)
            stdout, stderr = p.communicate()
            ret = p.returncode

            if ret != 0:
                raise CompilerError(
                    "Solc has experienced a fatal error (code {}).\n\n{}".format(
                        ret, stderr.decode("utf-8")
                    )
                )
        except FileNotFoundError:
            raise CompilerError(
                (
                    "Compiler not found. Make sure that solc is installed and in PATH, "
                    "or the SOLC environment variable is set."
                )
            )
        return stdout.decode()

    def import_solidity_file(
        self, file_path: str, solc_binary: str = "solc", solc_args: str = None
    ):
        self._nodes = set()
        self._edges = defaultdict(set)
        callgraph = self._get_callgraph_from_solidity_file(file_path, solc_binary, solc_args)
        self._parse_callgraph(callgraph)

    def _parse_callgraph(self, callgraph):
        lines = callgraph.split("\n")
        calls = filter(lambda x: "->" in x, lines)

        for call in calls:
            idx = call.find("->")
            caller = self._signature_break_down(call[:idx])
            caller = caller[1]+caller[2]
            callee = self._signature_break_down(call[idx+2:])
            callee = callee[1]+callee[2]

            self._nodes.add(caller)
            self._nodes.add(callee)
            self._edges[callee].add(caller)

    @staticmethod
    def _signature_break_down(source):
        contract_name = ""
        args = ""
        if '.' in source:
            split = source.split('.')
            contract_name = split[0]
            source = split[1]
        if '(' in source:
            idx = source.find('(')
            args = source[idx:]
            source = source[:idx]
        function_name = source
        return contract_name, function_name, args

    @staticmethod
    def _match(function, node):
        function = Callgraph._signature_break_down(function)
        node = Callgraph._signature_break_down(node)
        for i in range(len(function)):
            if function[i] and function[i] != node[i]:
                return False
        return True

    def _get_nodes(self, function):
        return [node for node in self._nodes if Callgraph._match(function, node)]

    def request_call_dependency(self, functions):
        nodes = list(set().union(*[self._get_nodes(function) for function in functions]))
        dependencies = deepcopy(nodes)
        while nodes:
            node = nodes.pop()
            new_nodes = list(filter(lambda x: x not in dependencies, self._edges[node]))
            dependencies.extend(new_nodes)
            nodes.extend(new_nodes)
        if 'constructor' in dependencies:
            dependencies = None
        return dependencies
