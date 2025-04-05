from rdflib import Graph, BNode, URIRef, Literal, Variable
from rdflib.plugins.sparql import algebra, parser
from typing import List, Dict, Optional, Set
import itertools
from Query.SimpleLiteral import SimpleLiteral
from Relaxation.QueryFailureAnalyzer import QueryFailureAnalyzer
from Query.ConjunctiveQueryClause import ConjunctiveQuery

class QueryRelaxer:
    """Implémentation principale de la stratégie de relaxation"""
    
    def __init__(self, query:ConjunctiveQuery, graph: Graph):
        self.original_query = query
        self.graph = graph
        self.relaxation_queue = []
        self.processed = set()
        
        # Initialisation des structures
        self.triples = self._parse_query_triples()
        self.mfs_list = QueryFailureAnalyzer.find_all_failing_causes(query,self.graph)
        self._init_relaxation_space()

    def _parse_query_triples(self) -> List[str]:
        """Extrait les triplets de la requête originale"""
        # parsed = parser.parseQuery(self.original_query)
        return self.original_query.clauses

    def _init_relaxation_space(self):
        """Prépare l'espace de relaxation initial"""
        self.relaxation_queue.append({
            'triples': self.triples.copy(),
            'relax_level': [0]*len(self.triples),
            'similarity': 1.0
        })

    def _generate_relaxations(self, current_state: Dict) -> List[Dict]:
        """Génère les relaxations possibles"""
        new_states = []
        for i in range(len(current_state['triples'])):
            if current_state['relax_level'][i] < self.max_relax_level:
                new_relax = current_state.copy()
                new_relax['relax_level'][i] += 1
                new_relax['triples'][i] = self._relax_triple(
                    current_state['triples'][i], 
                    new_relax['relax_level'][i]
                )
                new_relax['similarity'] *= self._get_similarity_factor(i)
                new_states.append(new_relax)
        return new_states

    def next_relaxation(self) -> Optional[str]:
        """Génère la prochaine requête relaxée valide"""
        while self.relaxation_queue:
            current = self.relaxation_queue.pop(0)
            state_hash = self._state_hash(current)
            if state_hash in self.processed:
                continue
            self.processed.add(state_hash)
            
            if self._is_valid_relaxation(current):
                return self._build_query(current)
            
            self.relaxation_queue.extend(self._generate_relaxations(current))
        
        return None

    def _is_valid_relaxation(self, state: Dict) -> bool:
        """Vérifie si la requête relaxée est valide (sans MFS)"""
        return not any(
            all(triple in state['triples'] for triple in mfs)
            for mfs in self.mfs_list
        )

    def _build_query(self, state: Dict) -> str:
        """Construit la requête SPARQL à partir de l'état courant"""
        return "SELECT * WHERE { " + " . ".join(state['triples']) + " }"
if __name__ == "__main__":
    # Exemple de graph RDF
    g = Graph()
    g.parse("graph.ttl", format="turtle")

    # Exemple de requête SPARQL
   # 2️⃣ Définition des clauses de la requête
    t1 = SimpleLiteral((Variable("p"), URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type"), URIRef("http://example.org/Lecturer")))
    t2 = SimpleLiteral((Variable("p"), URIRef("http://example.org/nationality"), Variable("n")))
    t3 = SimpleLiteral((Variable("p"), URIRef("http://example.org/teacherOf"), Literal("SW")))
    t4 = SimpleLiteral((Variable("p"), URIRef("http://example.org/age"), Literal(46)))

    # 3️⃣ Construction de la requête conjonctive
    query = ConjunctiveQuery()
    query.add_clause(t1)
    query.add_clause(t2)
    query.add_clause(t3)
    query.add_clause(t4)
    query.selected_vars = {"p", "n"}
    print(query.to_sparql())

    # Création d'une instance de QueryRelaxer et génération de requêtes relaxées
    relaxer = QueryRelaxer(query, g)
    
    print("Requêtes relaxées valides :")
    while (relaxed := relaxer.next_relaxation()) is not None:
        print(f"\n{relaxed}")
