from typing import List, Set
import re
from rdflib import URIRef, Literal as RDFLiteral, Variable as RDFVariable
from Query.SimpleLiteral import SimpleLiteral
from Query.ConjunctiveQueryClause import ConjunctiveQuery

class SparqlTripletParser:
    """
    Extrait les triplets (subject, predicate, object) d'une requête SPARQL,
    convertit en SimpleLiteral, et récupère les variables depuis SELECT.
    """
    def __init__(self, query: str):
        self.query_string: str = query
        self.triple_patterns: List[SimpleLiteral] = []
        self.variables: Set[str] = set()
        self.query = ConjunctiveQuery()

    def parse(self) -> None:
        """
        1. Extrait les variables de la clause SELECT (sans '?').
        2. Parcourt le bloc WHERE pour créer les SimpleLiteral.
        3. Remplit self.query.selected_vars et self.query.clauses.
        """
        # --- 1. Extraction des variables depuis SELECT ... WHERE ---
        m = re.search(r'(?i)SELECT\s+(.*?)\s+WHERE', self.query_string, re.DOTALL)
        if not m:
            raise ValueError("Clause SELECT introuvable ou mal formée")
        select_part = m.group(1)
        # toutes les occurrences de ?var
        self.variables = {var[1:] for var in re.findall(r'\?[A-Za-z0-9_]+', select_part)}
        self.query.selected_vars =self.variables

        # --- 2. Extraction du bloc WHERE ---
        start = self.query_string.find('{')
        end   = self.query_string.rfind('}')
        if start < 0 or end < 0 or start >= end:
            raise ValueError("Bloc WHERE mal formé")
        body = self.query_string[start+1:end].strip()

        # --- 3. Parcours ligne par ligne des triplets ---
        for line in body.splitlines():
            line = line.strip().rstrip('.')
            if not line:
                continue
            parts = line.split(None, 2)  # sujet, prédicat, objet
            if len(parts) != 3:
                raise ValueError(f"Pattern à 3 termes attendu, trouvé: {parts}")
            subj_str, pred_str, obj_str = parts

            subj = self._convert_term(subj_str)
            pred = self._convert_term(pred_str)
            obj  = self._convert_term(obj_str)

            triple = SimpleLiteral((subj, pred, obj))
            self.triple_patterns.append(triple)
            self.query.add_clause(triple)

    def _convert_term(self, term: str):
        """
        Convertit une chaîne SPARQL en instance RDF :
          - '?v'          -> RDFVariable('v')
          - '"..."^^<...>' -> RDFLiteral(val, datatype=URIRef)
          - '"..."'       -> RDFLiteral(val)
          - sinon         -> URIRef(term)
        """
        # Variable SPARQL
        if term.startswith('?'):
            return RDFVariable(term[1:])
        # Littéral typé
        if term.startswith('"'):
            # Type ^^<URI>
            if '^^<' in term:
                value_part, dtype_part = term.split('^^', 1)
                val = value_part.strip('"')
                # Cast int si possible
                if val.isdigit():
                    val = int(val)
                dtype = URIRef(dtype_part.strip('<>'))
                return RDFLiteral(val, datatype=dtype)
            # Littéral simple
            return RDFLiteral(term.strip('"'))
        # URIRef
        clean = term.strip().strip('<>').strip()
        # 2) on crée l'URIRef
        return URIRef(clean)

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
    sparql_query = '''SELECT ?x ?y ?z
WHERE {
    ?x <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://www.lehigh.edu/~zhp2/2004/0401/univ-bench.owl#GraduateStudent> .   
    ?x <http://www.lehigh.edu/~zhp2/2004/0401/univ-bench.owl#undergraduateDegreeFrom> ?y .
    ?x <http://www.lehigh.edu/~zhp2/2004/0401/univ-bench.owl#memberOf> ?z .
    ?y <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://www.lehigh.edu/~zhp2/2004/0401/univ-bench.owl#University> .     
    ?z <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://www.lehigh.edu/~zhp2/2004/0401/univ-bench.owl#Department> .     
    ?z <http://www.lehigh.edu/~zhp2/2004/0401/univ-bench.owl#subOrganizationOf> ?y .
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