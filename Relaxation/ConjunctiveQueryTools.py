from Query.ConjunctiveQueryClause import ConjunctiveQuery
from rdflib import Graph, Namespace, Literal, URIRef, RDF
from typing import List, Optional


class ConjunctiveQueryTools:

    def query_contains_in_list(list_query: list[ConjunctiveQuery], query: ConjunctiveQuery) -> bool:
        """
        Vérifie si une requête existe dans la liste par relation de sous-requête
        Version optimisée avec court-circuit et compréhension de générateur
        """
        return any(
            q.is_subquery(query) or query.is_subquery(q)
            for q in list_query
        )

    def maximal_factorization(query, mfs, graph: Graph) -> List['ConjunctiveQuery']:
        from Relaxation.QueryFailureAnalyzer import QueryFailureAnalyzer
        """
        Retourne une liste de facteurs maximaux pour 'query' par rapport à un MFS donné 'mfs'.
        L'algorithme procède ainsi :
        - On détermine l'ensemble D des clauses littérales de query qui ne sont pas déjà dans mfs.
        - Pour chaque clause de D, on essaie d'étendre de façon gloutonne le MFS en y ajoutant
            d'autres clauses de D tant que la requête reste défaillante (i.e. not_k_completed retourne True).
        - On conserve chaque extension (candidate) qui est maximale (aucune clause supplémentaire de D
            ne peut y être ajoutée sans que la requête ne devienne complète).
        Cette approche est heuristique et peut ne pas explorer toutes les combinaisons possibles, mais
        offre une alternative raisonnable à une recherche exhaustive (2^n).
        """
        factors = []
        # D est l'ensemble des clauses de query absentes du MFS.
        D = [lit for lit in query.clauses if lit not in mfs.clauses]
        
        # S'il n'y a aucune clause à ajouter, aucune factorisation n'est possible.
        if not D:
            return factors
        
        # Pour chaque clause de D, construire un facteur maximal candidate.
        for lit in D:
            candidate = mfs.clone()
            candidate.add(lit)
            # On travaille avec une copie des clauses restantes.
            remaining = [x for x in D if x != lit]
            changed = True
            while changed:
                changed = False
                # Essayer d'ajouter chacune des clauses restantes au candidat.
                for x in remaining[:]:
                    candidate2 = candidate.clone()
                    candidate2.add(x)
                    # Si en ajoutant x la requête reste défaillante, on intègre x dans le candidat.
                    if QueryFailureAnalyzer.not_k_completed(candidate2.to_sparql(), graph):
                        candidate.add(x)
                        remaining.remove(x)
                        changed = True
            # On ajoute candidate à la liste des facteurs si elle n'est pas redondante.
            if not any(candidate.is_subquery(f) or f.is_subquery(candidate) for f in factors):
                factors.append(candidate)
        
        return factors
