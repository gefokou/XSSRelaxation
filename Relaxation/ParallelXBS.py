import threading
from queue import Queue
from rdflib import Graph, URIRef, Literal, RDFS
from Query.ConjunctiveQueryClause import ConjunctiveQuery as Query
from Relaxation.XSSGenerator import XSSGenerator
from Relaxation.relaxtools import ConjunctiveQueryRelaxation, TripleRelaxation

class ParallelRelaxationStrategy:
    def __init__(self, Q: Query, D: Graph, k: int):
        """
        Constructeur de la stratégie de relaxation parallèle.
        
        Args:
            Q (Query): La requête initiale.
            D (Graph): La base de données RDF (un rdflib.Graph).
            k (int): Nombre de résultats minimum requis pour considérer une requête réparée.
        """
        self.Q = Q
        self.D = D
        self.k = k
        self.Res = []            # Liste des requêtes réparées (résultats)
        self.E = Queue()         # File des candidats issus de Xss (tuples (Q - x, x))
        self.Cand = Queue()      # File des candidats relaxés

    def delta(self) -> list:
        """
        Extrait les éléments candidats (δ) à partir de la requête Q.
        Pour chaque clause candidate x, calcule la requête Q privée de x.
        
        Returns:
            list: Une liste de tuples (Q - x, x).
        """
        delta_list = []
        # XSSGenerator.compute_xss(Q, D) renvoie la liste des clauses candidates
        Xss = XSSGenerator.compute_xss(self.Q, self.D)
        print(f"\n \n Xss: {Xss}")
        for xss in Xss:
            # Q.remove_clause(xss) retourne une nouvelle requête sans la clause xss
            diff_triples = set(self.Q.clauses)-set(xss.clauses)
            delta_query = Query()
            delta_query.clauses = diff_triples
            delta_list.append((delta_query, xss))
        return delta_list

    def producer(self):
        """
        Processus Producer qui, pour chaque candidat dans la file E,
        effectue la relaxation du triplet en parallèle et stocke les résultats dans Cand.
        """
        # Vérifier que la file E n'est pas vide
        if not self.E.empty():
            tmp_results = {}  # Dictionnaire pour stocker les relaxations par candidat

            def relax_task(candidate):
                # candidate est un tuple (Q - x, x)
                # On applique la relaxation sur la clause candidate (ici, on utilise le deuxième élément du tuple)
                query_relax =ConjunctiveQueryRelaxation(candidate[0], self.D, order=1)
                results = []
                # Récupération des triplets relaxés (pour cet exemple, on récupère la première clause de la requête relaxée)
                relaxed_queries = query_relax.relax_query()
    
                for rq in relaxed_queries:
                    results.append(rq)
                results.pop(0) 
                tmp_results[candidate] = results

            threads = []
            # Extraire tous les candidats présents dans la file E
            elements = list(self.E.queue)
            for candidate in elements:
                thread = threading.Thread(target=relax_task, args=(candidate,))
                threads.append(thread)
                thread.start()

            # Attendre la fin de tous les threads
            for thread in threads:
                thread.join()
            print(elements)
            # Pour chaque candidat, ajouter ses résultats relaxés dans la file Cand
            for candidate in elements:
                for relaxed_x in tmp_results.get(candidate, []):
                    self.Cand.put(relaxed_x)

    def consumer(self):
        """
        Processus Consumer qui parcourt la file E des candidats et évalue chaque requête réparée.
        Si une requête candidate retourne au moins k résultats (évaluée sur D),
        elle est ajoutée à la liste des résultats Res.
        
        Dans cet exemple, l'évaluation est simulée.
        """
        # Tant que la file E n'est pas vide, consommer les candidats
        while not self.E.empty():
            candidate_query, candidate_element = self.E.get()
            # Simulation de l'évaluation de la requête candidate sur la base D.
            # Ici, on suppose que la méthode evaluate_query retourne une liste de résultats.
            results = self.evaluate_query(candidate_query, self.D)
            if len(results) >= self.k:
                self.Res.append(candidate_query)
            self.E.task_done()

    def evaluate_query(self, query: Query, D: Graph) -> list:
        """
        Évalue la requête query sur la base de données D.
        Pour la démonstration, si la requête contient au moins une clause, on retourne
        une liste fictive de résultats.
        
        Returns:
            list: Liste de résultats fictifs.
        """
        # Simulation : si query a au moins une clause, renvoyer 10 résultats fictifs, sinon vide.
        if len(query.clauses) > 0:
            return [1] * 10
        else:
            return []

    def parallelxbs(self) -> list:
        """
        Exécute l'algorithme de relaxation parallèle.
        
        Returns:
            list: La liste des requêtes réparées (Res) qui satisfont le critère.
        """
        # Réinitialiser les résultats
        self.Res = []
        # Vider la file E si nécessaire
        while not self.E.empty():
            self.E.get()

        # Pour chaque candidat x (issu de Delta(Q)), on ajoute (Q - x, x) dans la file E.
        for candidate in self.delta():
            self.E.put(candidate)

        # Lancement des threads Producer et Consumer
        producer_thread = threading.Thread(target=self.producer)
        consumer_thread = threading.Thread(target=self.consumer)
        producer_thread.start()
        consumer_thread.start()
        producer_thread.join()
        consumer_thread.join()

        return self.Res
