import threading
from queue import PriorityQueue, Queue
from typing import List
from rdflib import URIRef, Literal, RDFS, Variable
from Query.ConjunctiveQueryClause import ConjunctiveQuery as Query
from Query.SimpleLiteral import SimpleLiteral
from Relaxation.EndpointMode.FindXss import XSSGenerator
from Relaxation.EndpointMode.relaxation import ConjunctiveQueryRelaxation, TripleRelaxation
import itertools
from Relaxation.EndpointMode.SimilarityEndpoint import SimilarityCalculator as sim
import time
import requests

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
    def __init__(self, Q: Query, D: str, k: int):
        """
        Constructor for the parallel relaxation strategy.

        Args:
            Q (Query): The initial conjunctive query
            D (str): URL du endpoint SPARQL local
            k (int): Minimum number of results required
        """
        self.Q = Q
        self.D = D  # L'URL du endpoint
        self.k = k
        self.xss = []  # List of XSS candidates
        self.Res = []     # List of responses (results)
        self.Req = []     # List of repaired queries (results)
        self.E = Queue()         # Queue of candidates from Delta (tuples (Q - x, x))
        self.Cand = PriorityQueue()      # Queue of relaxed candidates
        self.counter = itertools.count()  # Global counter
        self.similarity = sim(D)
        self.query_exec_count = 0  
        self.execution_time = 0.0  

    def delta(self) -> list:
        """Generate delta candidates using endpoint"""
        delta_list = []
        Xss = XSSGenerator.compute_xss(self.Q, self.D)  # Utilisation directe du endpoint
        print(f"\nXSS trouvees\n")
        for i, xss in enumerate(Xss, 1):
            print(f"XSS {i}:")
            print([j.label for j in xss.clauses])
            print("-"*50)
        for xss in Xss:
            sim=self.similarity.query_similarity(self.Q.clauses, xss.clauses)
            self.xss.append((xss, sim))
            diff_triples = set(self.Q.clauses) - set(xss.clauses)
            delta_query = Query()
            delta_query.clauses = list(diff_triples)
            delta_list.append((delta_query, xss))
        return delta_list

    def producer(self):
        """Parallel relaxation using endpoint"""
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
        """Query evaluation through endpoint"""
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
            simval = priority*-1
            
            # Exécution via endpoint SPARQL
            def execute_query(request):
                sparql_query = request.to_sparql()
                response = requests.post(
                    self.D,
                    data={"query": sparql_query},
                    headers={"Accept": "application/json"}
                )
                return response
            response = execute_query(request)
            
            self.query_exec_count += 1
            if response.status_code == 200:
                results = response.json()
                if results.get("results", {}).get("bindings"):
                    for binding in results.get("results", {}).get("bindings", []):
                        if len(self.Res) < self.k and binding not in self.Res:
                            self.Res.append(binding)
                    self.Req.append((request, simval))
            else:
                self.E.put(candidate)
        if len(self.Res) < self.k:
            for x in self.xss:
                if len(self.Res) < self.k:
                    self.Req.append((x[0], x[1]))
                    response = execute_query(x[0])
                    self.query_exec_count += 1
                    if response.status_code == 200:
                        results = response.json()
                        if results.get("results", {}).get("bindings"):
                            for binding in results.get("results", {}).get("bindings", []):
                                if len(self.Res) < self.k and binding not in self.Res:
                                    self.Res.append(binding)
            self.Cand.task_done()

    def parallelxbs(self):
        """Main algorithm with endpoint integration"""
        start_time = time.time()
        for candidate in self.delta():
            self.E.put(candidate)
        producer_thread = threading.Thread(target=self.producer)
        consumer_thread = threading.Thread(target=self.consumer)
        producer_thread.start()
        producer_thread.join()
        consumer_thread.start()
        consumer_thread.join()
        end_time = time.time()
        self.execution_time = end_time - start_time
        # return self.Res

class ParallelRelaxationSmartStrategy:
    def __init__(self, Q: Query, D: str, k: int):
        """
        Constructor for the smart strategy.

        Args:
            Q (Query): Initial query
            D (str): Endpoint SPARQL URL
            k (int): Minimum results required
        """
        self.xss=[]
        self.Q = Q
        self.D = D
        self.k = k
        self.Res = []
        self.Req = []
        self.listTester = []  # List of tested queries
        self.F = []       # List of failure sub queries
        self.E = Queue()
        self.Cand = PriorityQueue()
        self.counter = itertools.count()
        self.similarity = sim(D)
        self.query_exec_count = 0  
        self.execution_time = 0.0  

    # Les méthodes restantes conservent la même logique avec adaptation du endpoint
    # ... (le reste du code reste similaire avec remplacement des appels Graph par des requêtes SPARQL)
    def delta(self) -> list:
        """Generate delta candidates using endpoint"""
        delta_list = []
        Xss = XSSGenerator.compute_xss(self.Q, self.D)  # Utilisation directe du endpoint
        print(f"\nXSS trouvees\n")
        for i, xss in enumerate(Xss, 1):
            print(f"XSS {i}:")
            print([j.label for j in xss.clauses])
            print("-"*50)
        for xss in Xss:
            sim=self.similarity.query_similarity(self.Q.clauses, xss.clauses)
            self.xss.append((xss, sim))
            diff_triples = set(self.Q.clauses) - set(xss.clauses)
            delta_query = Query()
            delta_query.clauses = list(diff_triples)
            delta_list.append((delta_query, xss))
        return delta_list

    def producer(self):
        """Parallel relaxation using endpoint"""
        if not self.E.empty():
            tmp_results = {}

            def relax_task(candidate):
                query_relax = ConjunctiveQueryRelaxation(candidate[0], self.D, order=1)
                result = query_relax.relax_query()
                results=[]
                for cand in result:
                    valid = query_relax.is_relaxed_version_valid(cand)
                    if valid:
                        results.append((cand, candidate[1]))
                # results = [(i, candidate[1]) for i in result]
                # if results:
                #     results.pop(0)
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

    def GenFilter(self, candidate):
        """Failing sub-queries detection via endpoint"""
        print("\n Filter")
        if len(candidate[0].clauses)>1:
            list_candidate = [candidate[0], candidate[0]]
            test = self.generate_combinations(list_candidate)
            while test:
                i = test.pop(0)
                candidate_union = Query.conjunction_query_union(i, candidate[1])
                sparql_query = candidate_union.to_sparql()
                if candidate_union not in self.listTester:
                    self.listTester.append(candidate_union)
                    response = requests.post(
                        self.D,
                        data={"query": sparql_query},
                        headers={"Accept": "application/json"}
                    )
                    self.query_exec_count += 1
                    if response.status_code != 200 or not response.json().get("results", {}).get("bindings"):
                        self.F.append(i)
                        new_test = [j for j in test if not i.is_subquery(j)]
                        test = new_test
        else:
            self.F.append(candidate[0]) 

    def consumer(self):
        """Modified consumer with endpoint calls"""
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
                if j.is_subquery(candidate[0]):
                    elig = False
                i += 1
            if elig:
                print("Execution de la requete candidate")
                candidate_query = Query.conjunction_query_union(candidate[1], candidate[0])
                candidate_query.selected_vars = self.Q.selected_vars.copy()
                
                # Exécution via endpoint
                def execute_query(request):
                    sparql_query = request.to_sparql()
                    response = requests.post(
                        self.D,
                        data={"query": sparql_query},
                        headers={"Accept": "application/json"}
                    )
                    return response
                response = execute_query(candidate_query)
                
                self.query_exec_count += 1
                simval = priority*-1
                
                if response.status_code == 200 and response.json().get("results", {}).get("bindings"):
                    results = response.json()
                    print("Requete candidate valide avec des resultats\n")
                    for binding in results.get("results", {}).get("bindings"):
                        if len(self.Res) < self.k and binding not in self.Res:
                            self.Res.append(binding)
                    self.Req.append((candidate_query, simval))
                else:
                    self.E.put(candidate)
                    self.GenFilter(candidate)
            else:
                print("Requete candidate non valide")
                self.E.put(candidate)
            
        for x in self.xss:
            if len(self.Res) < self.k:
                self.Req.append((x[0], x[1]))
                response = execute_query(x[0])
            
                self.query_exec_count += 1
                if response.status_code == 200:
                    results = response.json()
                    for binding in results.get("results", {}).get("bindings", []):
                        if len(self.Res) < self.k and binding not in self.Res:
                            self.Res.append(binding)

        self.Cand.task_done()

    def parallelxbsv2(self):
        """
        Execute the smart parallel relaxation algorithm.
        
        Returns:
            list: The list of repaired queries (Res) satisfying the criterion.
        """
        start_time = time.time()  # Start time measurement
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