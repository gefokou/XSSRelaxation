from typing import List, Optional
from rdflib import Graph
from Query.ConjunctiveQueryClause import ConjunctiveQuery
from Relaxation.ConjunctiveQueryTools import ConjunctiveQueryTools

class QueryFailureAnalyzer:
    @staticmethod
    def not_k_completed(query_str: str, graph: Graph, k=0) -> bool:
        """
        Vérifie si la requête retourne au plus k solutions.
        """
        if query_str is None:
            raise ValueError("La requête ne peut être None")
        nb_solution = 0
        try:
            results = graph.query(query_str)
            for _ in results:
                nb_solution += 1
                if nb_solution > k:
                    break
        except Exception as e:
            print(f"Erreur lors de l'exécution de la requête : {e}")
        return nb_solution <= k
    
    
    @staticmethod
    def find_all_failing_causes(query, graph: Graph) -> List['ConjunctiveQuery']:
        """
        Recherche exhaustive de toutes les MFS d'une requête (coût potentiellement 2^n).
        """
        all_mfs = []
        if not QueryFailureAnalyzer.not_k_completed(query.to_sparql(), graph):
            return all_mfs

        if len(query.clauses) == 1:
            all_mfs.append(query.clone())
            return all_mfs

        is_mfs = True
        for element in list(query.clauses):
            query.remove(element)
            current_all_mfs = QueryFailureAnalyzer.find_all_failing_causes(query, graph)
            if current_all_mfs:
                is_mfs = False
                for one_mfs in current_all_mfs:
                    if not any(old_mfs.is_subquery(one_mfs) for old_mfs in all_mfs):
                        all_mfs.append(one_mfs)
            query.add(element,len(query.clauses))
        if is_mfs:
            all_mfs.append(query.clone())
        return all_mfs
    # @staticmethod
    # def find_a_failing_cause(query, graph: Graph) -> Optional['ConjunctiveQuery']:
    #     """
    #     Recherche récursivement une sous-requête minimale (MFS) responsable de l'échec.
    #     """
    #     if not QueryFailureAnalyzer.not_k_completed(query.to_sparql(), graph):
    #         return None

    #     if len(query.clauses) == 1:
    #         return query.clone()

    #     find_mfs = False
    #     failing_cause = None
    #     # Itération sur les clauses littérales (on travaille sur une copie de la liste pour éviter les problèmes d'indexation)
    #     for i, element in enumerate(query.clauses):
    #         query.remove(element)
    #         if QueryFailureAnalyzer.not_k_completed(query.to_sparql(), graph):
    #             mfs = QueryFailureAnalyzer.find_a_failing_cause(query, graph)
    #             if mfs is not None:
    #                 failing_cause = mfs
    #                 find_mfs = True
    #         query.add(i, element)
    #         if find_mfs:
    #             break

    #     return failing_cause if find_mfs else query.clone()

    # @staticmethod
    # def find_a_failing_cause_with_core(query, core) -> 'ConjunctiveQuery':
    #     """
    #     Version avec accumulateur. Ajoute progressivement les clauses causales dans 'core'.
    #     """
    #     if query:
    #         if core:
    #             if not QueryFailureAnalyzer.not_k_completed(query.to_sparql(), graph):
    #                 if QueryFailureAnalyzer.not_k_completed(core.to_sparql(), graph):
    #                     return core
    #     else:
    #         return core

    #     if len(query.clauses) == 1:
    #         core.add(query.clauses[0])
    #         return core

    #     # On retire la première clause
    #     element = query.removepos(0)  # Supposons que remove accepte un index
    #     temp_query = ConjunctiveQuery.conjunction_query_union(query, core)
    #     if not QueryFailureAnalyzer.not_k_completed(temp_query.to_sparql(), graph):
    #         core.add(element)
    #         core = QueryFailureAnalyzer.find_a_failing_cause_with_core(query, core, graph)
    #     else:
    #         core = QueryFailureAnalyzer.find_a_failing_cause_with_core(query, core, graph)
    #     query.add(0, element)
    #     return core

    