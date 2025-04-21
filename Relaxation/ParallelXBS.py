import threading
from queue import PriorityQueue, Queue
from typing import List
from rdflib import Graph, URIRef, Literal, RDFS, Variable
from Query.ConjunctiveQueryClause import ConjunctiveQuery as Query
from Query.SimpleLiteral import SimpleLiteral
from Relaxation.XSSGenerator import XSSGenerator
from Relaxation.relaxtools import ConjunctiveQueryRelaxation, TripleRelaxation
import itertools
from Relaxation.similarite import SimilarityCalculator as sim
import time

# ---------------------------
# Constants and Global Counters
# ---------------------------
SUPPRESS_NODE_LEVEL = -1    # Relaxation level for node suppression
LEVEL_ORDER = 0             # Relaxation order by level
SIM_ORDER = 1               # Relaxation order by similarity
HYBRID_ORDER = 2            # Hybrid relaxation order

num_resource_release = 0    # Counter for resource variables
num_pred_release = 0        # Counter for predicate variables

class ParallelRelaxationStrategy:
    def __init__(self, Q: Query, D: Graph, k: int):
        """
        Constructor for the parallel relaxation strategy.
        
        Args:
            Q (Query): The initial conjunctive query.
            D (Graph): The RDF database (an rdflib.Graph).
            k (int): Minimum number of results required for a repaired query.
        """
        self.Q = Q
        self.D = D
        self.k = k
        self.Res = []     # List of responses (results)
        self.Req = []     # List of repaired queries (results)
        self.E = Queue()         # Queue of candidates from Delta (tuples (Q - x, x))
        self.Cand = PriorityQueue()      # Queue of relaxed candidates
        self.counter = itertools.count()  # Global counter
        self.similarity = sim(D)
        self.query_exec_count = 0  # Counter for query executions
        self.execution_time = 0.0  # Total execution time

    def delta(self) -> list:
        """
        Extract candidate elements (δ) from the query Q.
        For each candidate clause x, compute the query Q without x.
        
        Returns:
            list: A list of tuples (Q - x, x).
        """
        delta_list = []
        Xss = XSSGenerator.compute_xss(self.Q, self.D)
        print(f"\nXss: {Xss}")
        for xss in Xss:
            diff_triples = set(self.Q.clauses) - set(xss.clauses)
            delta_query = Query()
            delta_query.clauses = list(diff_triples)
            delta_list.append((delta_query, xss))
        return delta_list

    def producer(self):
        """
        Producer process: For each candidate in the queue E,
        perform parallel relaxation using TripleRelaxation, and store
        the relaxed queries in the Cand queue.
        """
        if not self.E.empty():
            tmp_results = {}

            def relax_task(candidate):
                query_relax = ConjunctiveQueryRelaxation(candidate[0], self.D, order=1)
                result = query_relax.relax_query()
                results = [(i, candidate[1]) for i in result]
                if results:
                    results.pop(0)
                tmp_results[candidate] = results

            threads = []
            elements = list(self.E.queue)
            for candidate in elements:
                thread = threading.Thread(target=relax_task, args=(candidate,))
                threads.append(thread)
                thread.start()

            for thread in threads:
                thread.join()

            req = Query()
            for candidate in elements:
                for relaxed_query in tmp_results.get(candidate, []):
                    request = req.conjunction_query_union(relaxed_query[0], candidate[1])
                    sim_value = self.similarity.query_similarity(self.Q.clauses, request.clauses)
                    count = next(self.counter)
                    self.Cand.put((-sim_value, count, relaxed_query))

            while not self.E.empty():
                self.E.get()

    def consumer(self):
        """
        Consumer process: Evaluate candidates from Cand queue and build Res.
        """
        print("\n requetes candidates:\n")
        while len(self.Res) < self.k and not self.Cand.empty():
            priority, count, candidate = self.Cand.get()
            print(candidate[0].to_sparql())
            print("\n similarity:")
            print(priority)
            print("\n")
            req = Query()
            request = req.conjunction_query_union(candidate[0], candidate[1])
            request.selected_vars = self.Q.selected_vars.copy()
            simval = self.similarity.query_similarity(self.Q.clauses, request.clauses)
            results = request.execute(self.D)
            self.query_exec_count += 1  # Increment query execution counter
            if results:
                for i in results.bindings:
                    if i not in self.Res and len(self.Res) < self.k:
                        self.Res.append(i)
                self.Req.append((request, simval))
            else:
                self.E.put(candidate)
            
            self.Cand.task_done()

    def parallelxbs(self):
        """
        Execute the complete parallel relaxation algorithm.
        
        Returns:
            list: The list of repaired queries (Res) satisfying the criterion.
        """
        start_time = time.time()  # Start time measurement
        self.Res = []
        for candidate in self.delta():
            self.E.put(candidate)
        producer_thread = threading.Thread(target=self.producer)
        consumer_thread = threading.Thread(target=self.consumer)
        producer_thread.start()
        producer_thread.join()
        consumer_thread.start()
        consumer_thread.join()
        end_time = time.time()  # End time measurement
        self.execution_time = end_time - start_time
        print(f"Nombre d'exécutions de requêtes : {self.query_exec_count}")
        print(f"Temps d'exécution : {self.execution_time:.2f} secondes")

class ParallelRelaxationSmartStrategy:
    def __init__(self, Q: Query, D: Graph, k: int):
        """
        Constructor for the smart parallel relaxation strategy.
        
        Args:
            Q (Query): The initial conjunctive query.
            D (Graph): The RDF database (an rdflib.Graph).
            k (int): Minimum number of results required for a repaired query.
        """
        self.Q = Q
        self.D = D
        self.k = k
        self.Res = []
        self.Req = []
        self.F = []       # List of failure sub queries
        self.E = Queue()
        self.Cand = PriorityQueue()
        self.counter = itertools.count()
        self.similarity = sim(D)
        self.query_exec_count = 0  # Counter for query executions
        self.execution_time = 0.0  # Total execution time

    @staticmethod
    def generate_combinations(queries: List[Query]) -> List[Query]:
        """
        Generate all non-redundant combinations of query clauses.
        """
        clauses_sets = [q.clauses for q in queries]
        combinations = itertools.product(*clauses_sets)
        seen = set()
        result = []
        for combo in combinations:
            merged = []
            for clause in combo:
                if clause not in merged:
                    merged.append(clause)
            key = tuple(merged)
            if key not in seen:
                seen.add(key)
                q = Query()
                q.clauses = merged
                result.append(q)
        return result

    def delta(self) -> list:
        """
        Extract candidate elements (δ) from the query Q.
        
        Returns:
            list: A list of tuples (Q - x, x).
        """
        delta_list = []
        Xss = XSSGenerator.compute_xss(self.Q, self.D)
        print(f"\nXSS trouvees\n")
        for i, xss in enumerate(Xss, 1):
            print(f"XSS {i}:")
            print([j.label for j in xss.clauses])
            print("-"*50)
        for xss in Xss:
            diff_triples = set(self.Q.clauses) - set(xss.clauses)
            delta_query = Query()
            delta_query.clauses = list(diff_triples)
            delta_list.append((delta_query, xss))
        return delta_list

    def producer(self):
        """
        Producer process: Relax candidates and store in Cand queue.
        """
        if not self.E.empty():
            tmp_results = {}

            def relax_task(candidate):
                query_relax = ConjunctiveQueryRelaxation(candidate[0], self.D, order=1)
                result = query_relax.relax_query()
                results = [(i, candidate[1]) for i in result]
                if results:
                    results.pop(0)
                tmp_results[candidate] = results

            threads = []
            elements = list(self.E.queue)
            for candidate in elements:
                thread = threading.Thread(target=relax_task, args=(candidate,))
                threads.append(thread)
                thread.start()

            for thread in threads:
                thread.join()

            req = Query()
            for candidate in elements:
                for relaxed_query in tmp_results.get(candidate, []):
                    request = req.conjunction_query_union(relaxed_query[0], candidate[1])
                    sim_value = self.similarity.query_similarity(self.Q.clauses, request.clauses)
                    count = next(self.counter)
                    self.Cand.put((-sim_value, count, relaxed_query))

            while not self.E.empty():
                self.E.get()

    def GenFilter(self, candidate):
        """
        Implement GenFilter algorithm to identify failing sub-queries.
        """
        list_candidate = [candidate[0], candidate[0]]
        test = self.generate_combinations(list_candidate)
        while test:
            i = test.pop(0)
            candidate_union = Query.conjunction_query_union(i, candidate[1])
            if not candidate_union.execute(self.D):
                self.query_exec_count += 1  # Increment query execution counter
                self.F.append((i, candidate[1]))
                new_test = [j for j in test if not i.is_subquery(j)]
                test = new_test

    def consumer(self):
        """
        Consumer process: Evaluate candidates with eligibility check.
        """
        print("\n requetes candidates:\n")
        while len(self.Res) < self.k and not self.Cand.empty():
            priority, count, candidate = self.Cand.get()
            print(candidate[0].to_sparql())
            print("\n similarity:")
            print(priority)
            print("\n")
            elig = True
            i = 0
            while i < len(self.F) and elig:
                j = self.F[i]
                if j[0].is_subquery(candidate[0]):
                    elig = False
                i += 1
            if elig:
                candidate_query = Query.conjunction_query_union(candidate[1], candidate[0])
                candidate_query.selected_vars = self.Q.selected_vars.copy()
                results = candidate_query.execute(self.D)
                self.query_exec_count += 1  # Increment query execution counter
                simval = self.similarity.query_similarity(self.Q.clauses, candidate_query.clauses)
                if results:
                    for i in results.bindings:
                        if i not in self.Res and len(self.Res) < self.k:
                            self.Res.append(i)
                    self.Req.append((candidate_query, simval))
                else:
                    self.E.put(candidate)
                    self.GenFilter(candidate)
            else:
                self.E.put(candidate)
            self.Cand.task_done()

    def parallelxbsv2(self):
        """
        Execute the smart parallel relaxation algorithm.
        
        Returns:
            list: The list of repaired queries (Res) satisfying the criterion.
        """
        start_time = time.time()  # Start time measurement
        while not self.E.empty():
            self.E.get()
        for candidate in self.delta():
            cqr = ConjunctiveQueryRelaxation(candidate[0], self.D, order=1)
            relaxed_versions = cqr.relax_query()
            req = Query()
            for i, cand in enumerate(relaxed_versions):
                valid = cqr.is_relaxed_version_valid(cand)
                if valid:
                    request = req.conjunction_query_union(cand, candidate[1])
                    sim_value = self.similarity.query_similarity(self.Q.clauses, request.clauses)
                    count = next(self.counter)
                    self.Cand.put((-sim_value, count, (cand, candidate[1])))

        producer_thread = threading.Thread(target=self.producer)
        consumer_thread = threading.Thread(target=self.consumer)
        consumer_thread.start()
        consumer_thread.join()
        producer_thread.start()
        producer_thread.join()
        end_time = time.time()  # End time measurement
        self.execution_time = end_time - start_time