from typing import List, Tuple, Set

from rdflib import URIRef, Literal as RDFLiteral, Variable as RDFVariable
from Query.SimpleLiteral import SimpleLiteral
from Query.ConjunctiveQueryClause import ConjunctiveQuery

class SparqlTripletParser:
    """
    Extrait les triplets (subject, predicate, object) d'une requête SPARQL
    et les convertit en instances SimpleLiteral avec types RDF adaptés.
    """
    def __init__(self, query: str):
        """
        :param query: chaîne SPARQL complète contenant un bloc WHERE { ... }
        """
        self.query_string: str = query
        self.triple_patterns: List[SimpleLiteral] = []
        self.variables: Set[str] = set()
        self.query = ConjunctiveQuery()

    def parse(self) -> None:
        """
        Analyse la requête SPARQL et construit:
        - une liste de SimpleLiteral((s,p,o))
        - un ConjunctiveQuery avec clauses ajoutées
        - l'ensemble des variables sans '?'
        """
        # Extraire contenu entre { et }
        start = self.query_string.find('{')
        end   = self.query_string.rfind('}')
        if start < 0 or end < 0:
            raise ValueError("Bloc WHERE mal formé")
        body = self.query_string[start+1:end]

        # Parcours ligne par ligne
        for line in body.splitlines():
            line = line.strip().rstrip('.')
            if not line:
                continue
            parts = line.split(None, 2)
            if len(parts) != 3:
                raise ValueError(f"Pattern à 3 termes attendu, trouvé: {parts}")
            subj_str, pred_str, obj_str = parts
            subj = self._convert_term(subj_str)
            pred = self._convert_term(pred_str)
            obj  = self._convert_term(obj_str)

            # Construire le SimpleLiteral et l'ajouter
            triple = SimpleLiteral((subj, pred, obj))
            self.triple_patterns.append(triple)
            self.query.add_clause(triple)

            # Recenser variables
            for term in (subj, obj):
                if isinstance(term, RDFVariable):
                    self.variables.add(str(term))

        # Stocker les variables sélectionnées
        self.query.selected_vars = {v for v in self.variables}

    def _convert_term(self, term: str):
        """
        Convertit une chaîne SPARQL en instance RDF:
        - '?v'          -> RDFVariable('v')
        - '"..."^^<...>' -> RDFLiteral(val, datatype=URIRef)
        - '"..."'     -> RDFLiteral(val)
        - sinon        -> URIRef(term)
        """
        # Variable SPARQL
        if term.startswith('?'):
            return RDFVariable(term[1:])
        # Typé littéral
        if term.startswith('"'):
            # Ex: "46"^^<...>
            if '^^<' in term:
                value_part, dtype_part = term.split('^^', 1)
                value = value_part.strip('" "')
                dtype = URIRef(dtype_part.strip('<>'))
                # caster numérique si possible
                try:
                    if value.isdigit():
                        value = int(value)
                except Exception:
                    pass
                return RDFLiteral(value)
            # Littéral simple
            return RDFLiteral(term.strip('" "'))
        # URIRef
        return URIRef(term.strip('< >'))

    def get_triple_patterns(self) -> List[SimpleLiteral]:
        return self.triple_patterns

    def get_variables(self) -> Set[str]:
        return self.variables

# # Exemple d'utilisation
# if __name__ == '__main__':
#     sparql_query = '''
#     SELECT ?p ?n WHERE {
#         ?p <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://example.org/Lecturer> .
#         ?p <http://example.org/nationality> ?n .
#         ?p <http://example.org/teacherOf> "SW" .
#         ?p <http://example.org/age> "46"^^<http://www.w3.org/2001/XMLSchema#integer> .
#     }'''

#     parser = SparqlTripletParser(sparql_query)
#     parser.parse()
#     for t in parser.get_triple_patterns():
#         print(t)
#     print("Vars:", parser.get_variables())


# Exemple d'utilisation:
if __name__ == '__main__':
    sparql_query = '''SELECT ?p ?n
WHERE {
?p <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://example.org/Lecturer> .
?p <http://example.org/nationality> ?n . 
?p <http://example.org/teacherOf> "SW" .
?p <http://example.org/age> "46"^^<http://www.w3.org/2001/XMLSchema#integer> .
}'''

    parser = SparqlTripletParser(sparql_query)
    parser.parse()
    # print("Triplets extraits:", parser.get_triple_patterns())
    print("Variables:", parser.get_variables())
    print("Requête conjonctive :")
    print(parser.query.to_sparql())
    for i in parser.query.clauses:
        print(i)


# if __name__ == "__main__":
#     # Exemple d'utilisation
#     query='''SELECT ?p ?n
# WHERE {
# ?p <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://example.org/Lecturer> .  # t0
# ?p <http://example.org/nationality> ?n .  # t1
# ?p <http://example.org/teacherOf> "SW" .  # t2
# ?p <http://example.org/age> "46"^^<http://www.w3.org/2001/XMLSchema#integer> .  # t3
# }'''
#     cq = SPARQLToConjunctiveQuery().parse(query)
#     print(cq.to_sparql())
#     # Affiche la requête conjonctive résultante
#     print("Requête conjonctive :")
#     print(cq.to_sparql())
#     print("Variables sélectionnées :")
#     print(cq.selected_vars)
#     print("Clauses :")
#     for clause in cq.clauses:
#         print(clause.label)     