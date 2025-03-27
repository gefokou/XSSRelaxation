from rdflib.plugins.sparql import parser, algebra
from rdflib import Variable, Graph
from typing import Set, List
from rdflib.plugins.sparql.processor import SPARQLResult

class FilterLiteral:
    _counter = 0

    def __init__(self, filter_expr: str):
        self.filter_expr = filter_expr
        self._label = f"F{FilterLiteral._counter}"
        FilterLiteral._counter += 1
        
        self.mentioned_vars: Set[str] = self._extract_vars()
        self.selected_vars: Set[str] = set()

    def _extract_vars(self) -> Set[str]:
        """méthode d'extraction des variables"""
        query_str = f"SELECT * WHERE {{ FILTER({self.filter_expr}) }}"
        parsed = parser.parseQuery(query_str)
        
        vars_found = set()
        
        def collect_vars(node):
            if isinstance(node, Variable):
                var_name = node.n3()[1:]  # Retire le '?' initial
                vars_found.add(var_name)
                
        algebra.traverse(parsed, collect_vars)
        return vars_found

    # Le reste du code reste inchangé...
    @property
    def clause_type(self) -> str:
        return "FILTER_CLAUSE"

    def add_selected_variable(self, var_name: str):
        if var_name in self.mentioned_vars:
            self.selected_vars.add(var_name)

    def add_selected_variables(self, variables: List[str]):
        for var in variables:
            self.add_selected_variable(var)

    @property
    def is_star_clause(self) -> bool:
        return len(self.selected_vars) == 0

    def to_sparql(self) -> str:
        select_clause = "SELECT *" if self.is_star_clause else f"SELECT {' '.join(f'?{v}' for v in self.selected_vars)}"
        return f"""
        {select_clause}
        WHERE {{
            FILTER ({self.filter_expr})
        }}
        """

    def execute(self, graph: Graph) -> SPARQLResult:
        from rdflib.plugins.sparql import prepareQuery
        query = prepareQuery(self.to_sparql())
        return graph.query(query)

    def __str__(self) -> str:
        return self.filter_expr

    @property
    def label(self) -> str:
        return self._label