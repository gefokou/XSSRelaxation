import threading
from queue import Queue
from rdflib import Graph, URIRef, Literal, RDFS, Variable
from Query.ConjunctiveQueryClause import ConjunctiveQuery as Query
from Query.SimpleLiteral import SimpleLiteral
from Relaxation.XSSGenerator import XSSGenerator
from Relaxation.relaxtools import ConjunctiveQueryRelaxation, TripleRelaxation
import itertools

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
        self.Res = []            # List of repaired queries (results)
        self.E = Queue()         # Queue of candidates from Delta (tuples (Q - x, x))
        self.Cand = Queue()      # Queue of relaxed candidates

    def delta(self) -> list:
        """
        Extract candidate elements (δ) from the query Q.
        For each candidate clause x, compute the query Q without x.
        
        Returns:
            list: A list of tuples (Q - x, x).
        """
        delta_list = []
        # XSSGenerator.compute_xss(Q, D) returns the list of candidate clauses.
        Xss = XSSGenerator.compute_xss(self.Q, self.D)
        print(f"\nXss: {Xss}")
        for xss in Xss:
            # Q.remove_clause(xss) returns a new query without clause xss.
            # Here we assume Q.clauses is a list; we compute the difference.
            diff_triples = set(self.Q.clauses) - set(xss.clauses)
            delta_query = Query()
            # Assign the set as list; assure type compatibility as needed.
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
            tmp_results = {}  # Dictionary to store relaxations for each candidate

            def relax_task(candidate):
                # Candidate is a tuple (Q - x, x)
                # We apply relaxation on candidate[0] (or candidate[1] according to design)
                query_relax = ConjunctiveQueryRelaxation(candidate[0], self.D, order=1)
                result = query_relax.relax_query()
                # Optionally, remove the original query from the results (if present)
                # For instance, results.pop(0) if we are sure the original is first.
                results=[]
                for i in result:
                    results.append((i,candidate[1]))
                # Here we assume that the first element of the result is the relaxed query.
                if results:
                    # Here we remove the original query if it is identical
                    if results[0][0].clauses == self.Q.clauses:
                        results.pop(0)
                tmp_results[candidate] = results

            threads = []
            # Extract all candidates present in the E queue
            elements = list(self.E.queue)
            for candidate in elements:
                thread = threading.Thread(target=relax_task, args=(candidate,))
                threads.append(thread)
                thread.start()

            for thread in threads:
                thread.join()

            # For each candidate, add its relaxed queries to Cand.
            for candidate in elements:
                for relaxed_query in tmp_results.get(candidate, []):
                    self.Cand.put(relaxed_query)

    def consumer(self):
        """
        Consumer process according to Algorithm 4:
        
        While the number of repaired queries in Res is less than k 
        and the Cand queue is not empty:
            - Dequeue a candidate x from Cand.
            - Evaluate the query: If the evaluation of (x[0] ∧ x[1]) is not empty,
              and if it is not already in Res, then add it to Res.
            - Otherwise, re-enqueue x in E.
        """
        element = list(self.Cand.queue)
        for i in element:
            print(i)
            
        while len(self.Res) < self.k and not self.Cand.empty():
            candidate = self.Cand.get()
            request=Query()
            request.conjunction_query_union(candidate[0],candidate[1])
            print(request)
            # In our setting, candidate is assumed to be a repaired query (already the result of relaxing (Q - x) ∧ x).
            # We simulate an evaluation of candidate on D.
            eval_results = request.execute(self.D)
            if eval_results:  # If evaluation is not empty
                # If candidate is not already in Res, add it.
                if eval_results not in self.Res:
                    self.Res.append(eval_results)
            else:
                # If evaluation is empty, re-enqueue candidate in E for further processing.
                self.E.put(candidate)
            self.Cand.task_done()


    def parallelxbs(self) -> list:
        """
        Execute the complete parallel relaxation algorithm.
        
        Returns:
            list: The list of repaired queries (Res) satisfying the criterion.
        """
        self.Res = []  # Reset results
        
        # Empty the candidate queue E if needed.
        while not self.E.empty():
            self.E.get()
        
        # For each candidate from Delta(Q), enqueue (Q - x, x) into E.
        for candidate in self.delta():
            self.E.put(candidate)
        
        # Start Producer and Consumer threads.
        producer_thread = threading.Thread(target=self.producer)
        consumer_thread = threading.Thread(target=self.consumer)
        producer_thread.start()
        consumer_thread.start()
        producer_thread.join()
        consumer_thread.join()
        
        return self.Res
