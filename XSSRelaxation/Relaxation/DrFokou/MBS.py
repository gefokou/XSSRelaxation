import heapq
from typing import List, Set, Tuple
from rdflib import Graph
from Query.ConjunctiveQueryClause import ConjunctiveQuery as Query
from Relaxation.XSSGenerator import XSSGenerator
from Relaxation.EndpointMode.relaxation import ConjunctiveQueryRelaxation
from Relaxation.EndpointMode.SimilarityEndpoint import SimilarityCalculator
from Relaxation.EndpointMode.FindMFS import QueryFailureAnalyzer
from Relaxation.parser2 import expand_sparql
from Relaxation.parser import SparqlTripletParser
import requests
import itertools
import time
from queue import PriorityQueue, Queue

class MFSBasedRelaxationStrategy:
    def __init__(self, Q: Query, D:str, k: int):
        """
        Implémente la stratégie de relaxation MBS (Minimal Failure Sets).

        Args:
            Q: requête conjunctive échouée (ConjunctiveQuery)
            D: base RDF (rdflib.Graph)
            k: nombre de résultats alternatifs attendus
        """
        self.Q = Q
        self.D = D
        self.k = k
        self.Res: List = []
        self.req=[]
        # Construction des MFS : complémentaires des XSS maximaux
        self.MFS_list= QueryFailureAnalyzer(D).find_all_failing_causes(Q)
        self.RQ=PriorityQueue()
        self.counter = itertools.count()
        self.RQ.put((-1.0, next(self.counter), Q))
        # # File priorité des requêtes relaxées: (−similarité, requête)
        # self.heap: List[Tuple[float, Query]] = []
        # heapq.heappush(self.heap, (-1.0, Q))

        # Marquage des requêtes insérées et échouées
        self.inserted: Set[Query] = {Q}
        self.failed: Set[Query] = {Q}
        # Calculateur de similarité
        self.sim_calc = SimilarityCalculator(D)
        self.query_exec_count = 0  
        self.execution_time = 0.0

    def relax(self) -> List:
        """
        Exécute l'algorithme MBS et renvoie les top-k bindings.
        """
        start_time = time.time()
        if not self.MFS_list:
            print("Aucune MFS trouvée, la requête initiale est valide.")
            return []
        while self.RQ and len(self.Res) < self.k:
            neg_sim,_,Qi = self.RQ.get()
            sim_val = -neg_sim

            # Si Qi n'est pas bloquée, exécution et collecte des résultats
            if Qi not in self.failed:
                def execute_query(request):
                    sparql_query = request.to_sparql()
                    response = requests.post(
                        self.D,
                        data={"query": sparql_query},
                        headers={"Accept": "application/json"}
                    )
                    return response
                response = execute_query(Qi)
                self.query_exec_count += 1
                if response.status_code == 200:
                    results = response.json()
                    if results.get("results", {}).get("bindings"):
                        for binding in results.get("results", {}).get("bindings", []):
                            if len(self.Res) < self.k and binding not in self.Res:
                                self.Res.append(binding)
                        self.req.append((Qi,sim_val))
            relax=ConjunctiveQueryRelaxation(Qi, self.D,1)
            relaxversion = relax.relax_query()
            # Génération de chaque requête fille en relaxant un triplet
            for Qc in relaxversion:
                    if Qc not in self.inserted:
                        Qc.selected_vars=self.Q.selected_vars.copy()

                        self.inserted.add(Qc)

                        # Élagage : si un MFS reste intact dans Qc, on marque comme failed
                        if any(mfs.is_subquery(Qc) for mfs in self.MFS_list):
                            self.failed.add(Qc)
                            # Sinon, on calcule la similarité et on réenfile
                        else:
                            sim_qc = self.sim_calc.query_similarity(self.Q.clauses, Qc.clauses)
                            self.RQ.put((-sim_qc, next(self.counter), Qc))

        end_time = time.time()  # End time measurement
        self.execution_time = end_time - start_time
        return self.Res

if __name__ == "__main__":
    # Exemple d'utilisation
    sparql_query = """
    prefix ub: <http://www.lehigh.edu/~zhp2/2004/0401/univ-bench.owl#>
    select ?x ?y1 ?y2 ?y3 {
    ?x a ub:Professor;
    ub:worksFor <http://www.Department0.University0.edu>;
    ub:name ?y1;
    ub:emailAddress ?y2;
    ub:telephone ?y3.
}
"""

    devquery=expand_sparql(sparql_query)
    # print("\nRequête SPARQL développée :")
    # print(devquery)

    parser = SparqlTripletParser(devquery)
    parser.parse()
    query= parser.query
    print("Requête conjonctive :")
    print(query.to_sparql())
    # Create an RDF graph D (can be loaded or built dynamically)
    D = "http://localhost:3030/ds/query"

    mbs_strategy = MFSBasedRelaxationStrategy(query, D, k=50)
    print("\n MFS trouvées :\n")
    for i, mfs in enumerate(mbs_strategy.MFS_list, 1):
        print(f"MFS {i} :", [cl.label for cl in mfs.clauses])
    print("\n")
    results = mbs_strategy.relax()
    print("\n")
    print("Requêtes relaxées valides :")
    print("\n")
    for rq in mbs_strategy.req:
        print(rq[0].to_sparql())
        print(f"Similarity:{rq[1]}")
        print("\n")
    for res in results:
        print("Resultat:\n")
        print(res)
        print("\n")
    print("Nombre de requêtes exécutées :", mbs_strategy.query_exec_count)
    print("Temps d'exécution total :", mbs_strategy.execution_time, "s")
    print("nombre de resultats:",len(mbs_strategy.Res))