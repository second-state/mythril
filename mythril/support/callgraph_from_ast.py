from collections import defaultdict
import json
from subprocess import PIPE, Popen
import tempfile

from mythril.exceptions import CompilerError

callable_name_list = ["FunctionDefinition", "ModifierDefinition"]

def _get_name_from_signature(signature):
    return signature.split("(")[0]

class CallGraph(object):
    def __init__(self):
        self._edges = None
        self._nodes = None
        self._id_to_signature = None

        self._reachability_map = None
        self._visited = None

    def _get_asts_from_solidity_file(
        self, file_path: str, solc_binary: str = "solc", solc_args: str = None
    ):
        cmd = [solc_binary, "--combined-json", "ast", file_path]
        if solc_args:
            cmd.extend(solc_args.split())

        # we need this to handle escape sequence correctly
        f = tempfile.TemporaryFile(mode='w+')
        try:
            p = Popen(cmd, stdout=f, stderr=PIPE)
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
        f.flush()
        f.seek(0)

        sources = json.load(f)['sources'].values()
        return [source['AST'] for source in sources]

    def import_solidity_file(
        self, file_path: str, solc_binary: str = "solc", solc_args: str = None
    ):
        self._edges = defaultdict(set)
        self._nodes = set()
        self._id_to_signature = {}

        self._reachability_map = {}
        self._visited = set()

        asts = self._get_asts_from_solidity_file(file_path, solc_binary, solc_args)
        # get ids we care about
        for ast in asts:
            self.get_callable_ids(ast)
        # get dependencies only for ids we care about
        for ast in asts:
            self.get_callable_signatures_and_dependencies(ast)

        for node in self._nodes:
            self._visited = set()
            self._reachability_map[node] = self._dfs(node)

    def go_deeper(self, func, node, *args):
        for children in node.get("children", []):
            func(children, *args)

    def get_callable_ids(self, node):
        if node["name"] in callable_name_list:
            self._nodes.add(node["id"])
        else:
            self.go_deeper(self.get_callable_ids, node)

    def get_callable_signatures_and_dependencies(self, node):
        self.parse_ast(node)

    def parse_ast(self, node):
        if node["name"] == "ContractDefinition":
            contract_name = node["attributes"]["name"]
            self.parse_contract(node, contract_name)
        else:
            self.go_deeper(self.parse_ast, node)

    def parse_contract(self, node, contract_name):
        if node["name"] in callable_name_list:
            callable_name = "%s.%s"%(contract_name, node["attributes"]["name"])
            callable_signature = "%s(%s)"%(callable_name,self.parse_signature(node))
            callable_id = node["id"]
            self._id_to_signature[callable_id] = callable_signature
            self.parse_callable(node, callable_id)
        else:
            self.go_deeper(self.parse_contract, node, contract_name)

    def parse_signature(self, node):
        # TODO Parse signature from AST when solc supports it.
        return "()"

    def parse_callable(self, node, callable_id):
        if "attributes" in node:
            if ref_id in self._nodes:
                self._edges[ref_id].add(callable_id)
        self.go_deeper(self.parse_callable, node, callable_id)

    def _get_nodes_and_edges_from_surya(self):
        cmd = ["surya", "graph", self._solidity_file]
        p = Popen(cmd, stdout=PIPE, stderr=PIPE)
        stdout, stderr = p.communicate()
        ret = p.returncode
        lines = stdout.decode().split("\n")
        calls = filter(lambda x
        : "->" in x, lines)

        self._edges = {}
        self._nodes = set()

        for call in calls:
            split = call.split()
            idx = split.index("->")
            caller = split[idx-1]
            callee = split[idx+1]

            if caller[0] != '"' or caller[-1] != '"':
                continue
            if callee[0] != '"' or callee[-1] != '"':
                continue

            caller = caller[1:-1].split(".")[1]
            callee = callee[1:-1].split(".")[1]

            if caller not in self._edges:
                self._edges[caller] = set()
            if callee not in self._edges:
                self._edges[callee] = set()

            self._nodes.add(caller)
            self._nodes.add(callee)
            self._edges[callee].add(caller)

    def _dfs(self, node):
        if node not in self._visited:
            self._visited.add(node)
            return set([node]).union(*[self._dfs(neighbor) for neighbor in self._edges[node]])
        else:
            return set()

    def signature_break_down(self, signature):
        contract_name = None
        args = None
        source = signature
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

    def get_signature_without_contract_name(self, function_id):
        signature = self._id_to_signature[function_id]
        contract_name, function_name, args = self.signature_break_down(signature)
        return function_name+args

    def match(self, function, pattern):
        function = self.signature_break_down(function)
        pattern = self.signature_break_down(pattern)
        for i in range(len(pattern)):
            if pattern[i] is not None and pattern[i] != function[i]:
                return False
        return True

    def get_ids(self, pattern):
        return {function_id for function_id, function\
                in self._id_to_signature.items() if self.match(function, pattern)}

    def request_call_dependency(self, functions):
        function_ids = set().union(*[self.get_ids(function)\
                                        for function in functions])
        dependency_ids = set().union(*[self._reachability_map[function_id]\
                                        for function_id in function_ids])
        dependencies = {self.get_signature_without_contract_name(dependency_id)\
                        for dependency_id in dependency_ids}
        return dependencies
