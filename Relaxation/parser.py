from typing import List, Tuple, Dict, Set

from Query.SimpleLiteral import SimpleLiteral
from Query.ConjunctiveQueryClause import ConjunctiveQuery

class SparqlTripletParser:
    """
    Cette classe se charge d'extraire les patterns de triplets (Basic Graph Patterns) d'une requête SPARQL.
    Elle identifie les triplets composés de (subject, predicate, object) et recense les variables présentes.
    """

    def __init__(self, query: str):
        """
        Initialise le parseur avec la requête SPARQL brute.

        :param query: La chaîne de caractères contenant la requête SPARQL complète.
        """
        # Stocke la requête d'entrée
        self.query_string: str = query
        # Liste où seront ajoutés les triplets (subject, predicate, object)
        self.triple_patterns: List[Tuple[str, str, str]] = []
        # Ensemble des variables rencontrées dans les triplets (ex: '?s', '?o')
        self.variables: Set[str] = set()
        self.query=ConjunctiveQuery()

    def parse(self) -> None:
        """
        Extrait les triplets de la requête SPARQL et les stocke dans self.triple_patterns.
        Analyse également les variables RDF (commençant par '?').

        Étapes détaillées:
        1. Trouver la zone de la requête entre les accolades '{' et '}'.
        2. Découper cette zone en lignes.
        3. Pour chaque ligne, retirer les points finaux et espaces superflus.
        4. Séparer en trois composants: subject, predicate, object.
        5. Ajouter le triplet à la liste et enregistrer les variables.
        """
        # 1. Repérer le début et la fin du bloc de triplets
        start_idx = self.query_string.find('{')
        end_idx   = self.query_string.rfind('}')

        # Si on ne trouve pas correctement les accolades, on lève une erreur explicite
        if start_idx == -1 or end_idx == -1 or start_idx >= end_idx:
            raise ValueError("La requête SPARQL doit contenir un bloc entre '{' et '}'.")

        # Extraire le corps contenant les triplets
        body = self.query_string[start_idx + 1 : end_idx].strip()

        # 2. Parcourir chaque ligne du corps
        for line in body.splitlines():
            # 3. Nettoyer la ligne: enlever espaces en début/fin et le point terminal
            clean_line = line.strip().rstrip('.')
            if not clean_line:
                # Ignorer les lignes vides
                continue

            # 4. Découper en sujet, prédicat, objet
            parts = clean_line.split()
            if len(parts) != 3:
                # Si la ligne ne correspond pas à un pattern de 3 éléments, on l'ignore ou lève une alerte
                raise ValueError(f"Ligne SPARQL mal formée: '{clean_line}'")

            subject, predicate, obj = parts
            triple=SimpleLiteral((subject, predicate, obj))
            # 5. Enregistrer le triplet
            self.triple_patterns.append((subject, predicate, obj))

            # Recenser les variables (tous les éléments commençant par '?')
            for term in (subject, predicate, obj):
                if term.startswith('?'):
                    self.variables.add(term[1:])
            self.query.add_clause(triple)
        self.query.selected_vars=self.variables
    def get_triple_patterns(self) -> List[Tuple[str, str, str]]:
        """
        Retourne la liste des triplets extraits.

        :return: Liste de tuples (subject, predicate, object)
        """
        return self.triple_patterns

    def get_variables(self) -> Set[str]:
        """
        Retourne l'ensemble des variables trouvées dans la requête.

        :return: Ensemble de chaînes (ex: {'?s', '?o'})
        """
        return self.variables

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