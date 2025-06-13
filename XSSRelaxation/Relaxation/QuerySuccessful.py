from rdflib import Graph
from rdflib.query import ResultRow
from typing import List, Optional, Set
import itertools
from abc import ABC, abstractmethod
from Relaxation.ConjunctiveQueryTools import ConjunctiveQueryTools
from Query.ConjunctiveQueryClause import ConjunctiveQuery
from Query.SimpleLiteral import SimpleLiteral

class QuerySuccessful:
    @staticmethod
    def has_top_k_answers(query: ConjunctiveQuery, Graph: Graph, nbr_answers: int=1) -> bool:
        if not query:
            raise ValueError("Invalid query")
        
        count = 0
        sparql_query = query.to_sparql()
        try:
            result = Graph.query(sparql_query)
            for _ in result:
                count += 1
                if count > nbr_answers:
                    return True
        except Exception as e:
            print(f"Query failed: {e}")
        return count > nbr_answers

    @staticmethod
    def find_a_success_query(query: ConjunctiveQuery, Graph: Graph, nbr_answers: int=1) -> Optional[ConjunctiveQuery]:
        if not query:
            return None
        
        queue = [query]
        visited = set()
        
        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            
            if QuerySuccessful.has_top_k_answers(current, Graph, nbr_answers):
                return current
            
            for i in range(len(current.clauses)):
                new_query = current.remove(i)
                if not ConjunctiveQueryTools.query_contains_in_list(queue, new_query):
                    queue.append(new_query)
        
        return None

    @staticmethod
    def find_all_success_queries(query: ConjunctiveQuery, Graph: Graph, nbr_answers: int=1) -> List[ConjunctiveQuery]:
        maxfactor = [query]
        all_max_subqueries = []
        
        while maxfactor:
            current = maxfactor.pop(0)
            max_subquery = QuerySuccessful.find_a_success_query(current, Graph, nbr_answers)
            
            if max_subquery:
                factors = ConjunctiveQueryTools.maximalFactorization(current, max_subquery)
                for factor in factors:
                    is_max = True
                    for i in range(len(maxfactor)-1, -1, -1):
                        if maxfactor[i].is_subquery(factor):
                            del maxfactor[i]
                        elif factor.is_subquery(maxfactor[i]):
                            is_max = False
                    if is_max:
                        maxfactor.append(factor)
                all_max_subqueries.append(max_subquery)
        
        return all_max_subqueries
