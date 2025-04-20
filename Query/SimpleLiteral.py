from rdflib import Graph, Variable, URIRef, BNode, Literal
from rdflib.plugins.sparql import prepareQuery
from rdflib.plugins.sparql.processor import SPARQLResult
from typing import List, Set, Optional

class SimpleLiteral:
    _counter = 0  
    # Compteur statique pour les labels
    
    def __init__(self, triple: tuple, clone:str=None):
        self.triple = triple
        self.label = f"t{SimpleLiteral._counter}"
        SimpleLiteral._counter += 1
        
        self.mentioned_vars: Set[str] = set()
        self.selected_vars: Set[str] = set()
        
        # Extraction des variables
        for component in triple:
            if isinstance(component, Variable):
                self.mentioned_vars.add(str(component))
    def set_label(self,label,num):
        self.label=f"{label}({num})"
    @property
    def clause_type(self) -> str:
        return "SIMPLE_CLAUSE"

    def get_triple_pattern(self) -> str:
        """Retourne la représentation textuelle du triplet"""
        return f"{self._format_node(self.triple[0])} {self._format_node(self.triple[1])} {self._format_node(self.triple[2])} ."

    def _format_node(self, node) -> str:
        """Formate les noeuds pour SPARQL"""
        if isinstance(node, Variable):
            return f"?{node}"
        if isinstance(node, (URIRef, Literal)):
            return node.n3()
        if isinstance(node, BNode):
            return f"_:{node}"
        return str(node)

    def add_selected_variable(self, var_name: str):
        """Ajoute une variable à la sélection si elle existe dans le triplet"""
        if var_name in self.mentioned_vars:
            self.selected_vars.add(var_name)

    def add_selected_variables(self, variables: List[str]):
        """Ajoute plusieurs variables à la sélection"""
        for var in variables:
            self.add_selected_variable(var)

    @property
    def is_star_clause(self) -> bool:
        """Vérifie si aucune variable n'est sélectionnée"""
        return len(self.selected_vars) == 0

    def to_sparql(self) -> str:
        """Génère la requête SPARQL correspondante"""
        select_clause = "SELECT *" if self.is_star_clause else f"SELECT {' '.join(f'?{v}' for v in self.selected_vars)}"
        
        return f"""
        {select_clause}
        WHERE {{
            {self.get_triple_pattern()}
        }}
        """

    def execute(self, graph: Graph) -> SPARQLResult:
        """Exécute la requête sur un graphe"""
        query = prepareQuery(self.to_sparql())
        return graph.query(query)

    def __repr__(self) -> str:
        return f"<SimpleLiteral {self.triple} | Vars: {self.mentioned_vars} | Selected: {self.selected_vars}>"