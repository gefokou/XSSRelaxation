from itertools import product
from typing import List, Set
from rdflib import Graph, Literal, URIRef
from Query.ConjunctiveQueryClause import ConjunctiveQuery
from Query.SimpleLiteral import SimpleLiteral
from Relaxation.QueryFailureAnalyzer import QueryFailureAnalyzer

class XSSGenerator:
    def generate_combinations(queries: List[ConjunctiveQuery]) -> List[ConjunctiveQuery]:
        """
        Génère toutes les combinaisons non redondantes entre les clauses des requêtes
        selon les exemples fournis
        """
        # Extraction des clauses uniques de chaque requête
        clauses_sets = [q.clauses for q in queries]
        
        # Génération du produit cartésien
        combinations = product(*clauses_sets)
        
        # Création des combinaisons uniques
        seen = set()
        result = []
        
        for combo in combinations:
            # Fusion des clauses en gardant l'ordre d'apparition
            merged = []
            for clause in combo:
                if clause not in merged:
                    merged.append(clause)
            
            # Vérification de l'unicité
            key = tuple(merged)
            if key not in seen:
                seen.add(key)
                q=ConjunctiveQuery()
                q.clauses=merged
                result.append(q)
        
        return result

    @staticmethod
    def compute_xss(main_query: ConjunctiveQuery,g:Graph) -> List[ConjunctiveQuery]:
        mfs_list = QueryFailureAnalyzer.find_all_failing_causes(main_query, g)
        print(f"MFS={mfs_list}")
        cand=XSSGenerator.generate_combinations(mfs_list)
        print(f"Cand={cand}")
        result_queries = []
        main_triples = main_query.clauses

        for pattern in cand:
            # Calcul de la différence : Q \ (ensemble des triplets de pattern)
            diff_triples = set(main_triples) - set(pattern.clauses)
            new_query = ConjunctiveQuery()
            new_query.clauses = diff_triples  # Affectation directe de l'ensemble résultant

            # Vérification pour s'assurer que new_query n'est pas une sous-requête
            # d'une autre déjà présente dans result_queries.
            is_subquery = False
            indices_to_remove = []
            for idx, existing_query in enumerate(result_queries):
                # Si new_query est inclus dans existing_query, on ne l'ajoute pas.
                if new_query.clauses <= set(existing_query.clauses):
                    is_subquery = True
                    break
                # Si l'existant est inclus dans new_query, on le retire.
                elif set(existing_query.clauses) <= new_query.clauses:
                    indices_to_remove.append(idx)
            if not is_subquery:
                # Supprimez les requêtes qui sont des sous-requêtes de new_query.
                for idx in sorted(indices_to_remove, reverse=True):
                    del result_queries[idx]
                result_queries.append(new_query)
        return result_queries
