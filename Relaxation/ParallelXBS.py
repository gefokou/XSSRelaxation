import threading
from queue import Queue
from typing import List
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
        self.Res = []     # List of responses (results)
        self.Req = []            # List of repaired queries (results)
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

            # For each candidate, create a thread to perform relaxation
            
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

            # vider E
            while not self.E.empty():
                self.E.get()
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
        while len(self.Res) < self.k and not self.Cand.empty():
            candidate = self.Cand.get()
            req=Query()
            request=req.conjunction_query_union(candidate[0],candidate[1])
            request.selected_vars = self.Q.selected_vars.copy()
            # Here we assume that candidate[0] is the relaxed query and candidate[1] is the clause to be added.
            # In our setting, candidate is assumed to be a repaired query (already the result of relaxing (Q - x) ∧ x).
            # We simulate an evaluation of candidate on D.
            eval_results = request.execute(self.D)
            if eval_results:  # If evaluation is not empty
                # If candidate is not already in Res, add it.
                if eval_results not in self.Res:
                    self.Res.append(eval_results)
                self.Req.append(request)   
            else:
                # If evaluation is empty, re-enqueue candidate in E for further processing.
                self.E.put(candidate)
            self.Cand.task_done()


    def parallelxbs(self):
        """
        Execute the complete parallel relaxation algorithm.
        
        Returns:
            list: The list of repaired queries (Res) satisfying the criterion.
        """
        self.Res = []  # Reset results
        
        # Empty the candidate queue E if needed.
        # while not self.E.empty():
        #     self.E.get()
        
        # For each candidate from Delta(Q), enqueue (Q - x, x) into E.
        for candidate in self.delta():
            self.E.put(candidate)
        # Start Producer and Consumer threads.
        producer_thread = threading.Thread(target=self.producer)
        consumer_thread = threading.Thread(target=self.consumer)
        producer_thread.start()
        producer_thread.join()
        consumer_thread.start()
        consumer_thread.join()


class ParallelRelaxationSmartStrategy:
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
        self.F = []       # List of failure sub queries
        self.E = Queue()         # Queue of candidates from Delta (tuples (Q - x, x))
        self.Cand = Queue()      # Queue of relaxed candidates

    @staticmethod
    def generate_combinations(queries: List[Query]) -> List[Query]:
        """
        Génère toutes les combinaisons non redondantes entre les clauses des requêtes
        selon les exemples fournis
        """
        # Extraction des clauses uniques de chaque requête
        clauses_sets = [q.clauses for q in queries]
        
        # Génération du produit cartésien
        combinations = itertools.product(*clauses_sets)
        
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
                q=Query()
                q.clauses=merged
                result.append(q)
        
        return result

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

            # For each candidate, create a thread to perform relaxation
            
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

            # vider E
            while not self.E.empty():
                self.E.get()

    def GenFilter(self, candidate):
        """
        Implémente l'algorithme GenFilter (Algorithm 9).
        
        Entrées:
            candidate: Un tuple (δ, xss) provenant d'un candidat.
        Modifie:
            self.F: Ajoute les sous-requêtes issues de candidate qui échouent.
        """
        list_candidate = [candidate[0],candidate[0]]
        test = self.generate_combinations(list_candidate)
        # Tant que test n'est pas vide :
        while test:
            # Déqueue le premier élément de test
            i = test.pop(0)
            # Construire candidate_union = (xss ∧ i)
            candidate_union = Query.conjunction_query_union(candidate[1], i)
            # Si l'évaluation de candidate_union sur D est vide, alors:
            if not candidate_union.execute(self.D):
                # Enfile i dans F
                self.F.append(i)
                # Pour chaque j restant dans test, si i est un sous-ensemble de j, retirer j de test.
                new_test = []
                for j in test:
                    if not i.is_subqueries(j):
                        new_test.append(j)
                test = new_test
            # Fin de while
        # Fin de GenFilter


    def consumer(self):
        """
        Processus Consumer (Algorithme 8).
        Tant que le nombre de résultats dans Res est inférieur à k et que la file Cand n'est pas vide:
            1. Défile un élément x de Cand.
            2. Initialise eligibility (elig) à True.
            3. Parcourt l'ensemble F: pour chaque sous-requête j ∈ F, si j est un sous-ensemble de x[0], alors elig devient False.
            4. Si elig est True:
                a. Calcule la requête candidate candidate_query = (x[0] ∧ x[1]) à l'aide de la fonction d'union (ici, on utilise la méthode statique de Query).
                b. Si l'évaluation de candidate_query sur D n'est pas vide et candidate_query n'est pas déjà dans Res, on l'ajoute à Res.
               Sinon, on enfile à nouveau x dans E et on appelle GenFilter(x).
            5. Si elig est False, on réenfile x dans E.
        """
        while len(self.Res) < self.k and not self.Cand.empty():
            x = self.Cand.get()  # x est un tuple (x_prime, x)
            elig = True
            i = 0
            while i < len(self.F) and elig:
                j = self.F[i]
                # Vérifier si la sous-requête j est un sous-ensemble de x_prime.
                # Nous supposons qu'une fonction is_subset(query1, query2) existe pour cela.
                if j.is_subquery(x[0]):
                    elig = False
                i += 1
            if elig:
                # On construit la requête candidate comme l'union (conjonction) de x_prime et x.
                candidate_query = Query.conjunction_query_union(x[1], x[0])
                candidate_query.selected_vars = self.Q.selected_vars.copy()
                results = candidate_query.execute(self.D)
                if results:
                    if results not in self.Res:
                        self.Res.append(results)
                        self.Req.append(candidate_query)
                else:
                    self.E.put(x)
                    self.GenFilter(x)
            else:
                self.E.put(x)
            self.Cand.task_done()


    def parallelxbsv2(self):
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
            cqr = ConjunctiveQueryRelaxation(candidate[0], self.D, order=1)
            relaxed_versions = cqr.relax_query()
      
            for i, cand in enumerate(relaxed_versions):
                valid = cqr.is_relaxed_version_valid(cand)
                if valid:
                    self.Cand.put((cand, candidate[1]))
        # Start Producer and Consumer threads.
        producer_thread = threading.Thread(target=self.producer)
        consumer_thread = threading.Thread(target=self.consumer)

        consumer_thread.start()
        consumer_thread.join()
        producer_thread.start()
        producer_thread.join()