from typing import List
from SPARQLWrapper import SPARQLWrapper, JSON
from rdflib import Literal, URIRef, Variable
from Query.ConjunctiveQueryClause import ConjunctiveQuery
from Query.SimpleLiteral import SimpleLiteral
from Relaxation.parser import SparqlTripletParser
from Relaxation.parser2 import expand_sparql

class QueryFailureAnalyzer:
    def __init__(self, endpoint_url: str):
        """
        :param endpoint_url: URL du endpoint SPARQL (ex. http://localhost:8000/sparql)
        """
        self.sparql = SPARQLWrapper(endpoint_url)
        self.sparql.setReturnFormat(JSON)

    def _ask(self, query_str: str) -> int:
        """
        Exécute count(*) sur le SELECT original pour savoir
        combien de solutions il renvoie (équivalent de .query() en mémoire).
        """
        # On encapsule la requête initiale dans un SELECT COUNT(*) pour limiter le transfert
        count_query = f"""
        SELECT (COUNT(*) AS ?c) WHERE {{
          {{
            {query_str}
          }}
        }}
        """
        self.sparql.setQuery(count_query)
        results = self.sparql.query().convert()
        return int(results["results"]["bindings"][0]["c"]["value"])

    def not_k_completed(self, query_str: str, k: int = 0) -> bool:
        """
        Vrai si la requête retourne au plus k solutions.
        """
        if not query_str:
            raise ValueError("La requête ne peut être vide")
        try:
            nb = self._ask(query_str)
        except Exception as e:
            print(f"Erreur endpoint SPARQL : {e}")
            # On considère que l'exécution a échoué => pas complété
            return True
        return nb <= k

    def find_all_failing_causes(
        self,
        query: ConjunctiveQuery,
    ) -> List[ConjunctiveQuery]:
        """
        Recherche exhaustive de toutes les MFS (Minimal Failing Subqueries)
        en interrogeant l'endpoint SPARQL pour savoir si une sous-requête échoue.
        """
        all_mfs = []

        sparql_str = query.to_sparql()
        # Si la requête principale renvoie >0 solutions, il n'y a pas d'échec
        if not self.not_k_completed(sparql_str, k=0):
            return all_mfs

        # Si un seul clause, c'est minimal
        if len(query.clauses) == 1:
            all_mfs.append(query.clone())
            return all_mfs

        is_mfs = True
        for clause in list(query.clauses):
            # Retirer la clause
            query.remove(clause)
            # Tester la sous‑requête
            sub_mfs = self.find_all_failing_causes(query)
            if sub_mfs:
                is_mfs = False
                for mfs in sub_mfs:
                    if not any(existing.is_subquery(mfs) for existing in all_mfs):
                        all_mfs.append(mfs)
            # Remettre la clause à la fin
            query.add(clause, len(query.clauses))
        # Si aucune sous-requête ne « casse » l’échec, la requête elle-même est MFS
        if is_mfs:
            all_mfs.append(query.clone())

        return all_mfs
    
if __name__ == "__main__":
    # Exemple d'utilisation
    endpoint_url = "http://localhost:3030/ds/query"
    analyzer = QueryFailureAnalyzer(endpoint_url)

    sparql_query = """
    prefix ub: <http://www.lehigh.edu/~zhp2/2004/0401/univ-bench.owl#>
    select ?x ?y1 ?y2 ?y3 {
    ?x a ub:Professor;
        ub:worksFor <http://www.Department0.University0.edu>;
        ub:name ?y1;
        ub:emailAddress ?y2;
        ub:telephone ?y3.
    }"""
    devquery=expand_sparql(sparql_query)
    parser = SparqlTripletParser(devquery)
    parser.parse()
    query= parser.query
    print(query.to_sparql())
    # 4️⃣ Exécution de l'analyse des échecs et extraction des MFS
    mfs_list = analyzer.find_all_failing_causes(query)
    print(f"Nombre de MFS trouvées : {len(mfs_list)}")
    # 5️⃣ Affichage des résultats
    print("\n🔎 Résultat : Minimal Failing Subqueries (MFS)\n")
    for i, mfs in enumerate(mfs_list, 1):
        print(f"MFS {i}: {mfs}")
        print(f"- Triplets: {[j.label for j in mfs.clauses]}\n \n")
    print(f"Fin")