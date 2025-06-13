from itertools import product
from typing import List
from Query.ConjunctiveQueryClause import ConjunctiveQuery
from Relaxation.EndpointMode.FindMFS import QueryFailureAnalyzer
from Relaxation.parser import SparqlTripletParser
from Relaxation.parser2 import expand_sparql

class XSSGenerator:
    @staticmethod
    def generate_combinations(queries: List[ConjunctiveQuery]) -> List[ConjunctiveQuery]:
        """
        Génère toutes les combinaisons non redondantes entre les clauses des requêtes
        selon les exemples fournis.
        """
        clauses_sets = [q.clauses for q in queries]
        combinations = product(*clauses_sets)

        seen = set()
        result = []
        for combo in combinations:
            # Fusion en conservant l'ordre
            merged = []
            for clause in combo:
                if clause not in merged:
                    merged.append(clause)

            key = tuple(merged)
            if key not in seen:
                seen.add(key)
                q = ConjunctiveQuery()
                q.clauses = merged
                result.append(q)
        return result

    @staticmethod
    def compute_xss(main_query: ConjunctiveQuery, endpoint_url: str) -> List[ConjunctiveQuery]:
        """
        Calcule les XSS (requêtes réparées) pour une requête conjonctive qui échoue,
        en interrogeant un endpoint SPARQL via QueryFailureAnalyzer.

        :param main_query: la requête initiale (ConjunctiveQuery)
        :param endpoint_url: URL du endpoint SPARQL (ex. http://localhost:8000/sparql)
        """
        # 1. Instanciation de l'analyseur sur l'endpoint
        analyzer = QueryFailureAnalyzer(endpoint_url)

        # 2. Calcul de toutes les MFS de la requête principale
        mfs_list = analyzer.find_all_failing_causes(main_query)

        print("\n MFS trouvées :\n")
        for i, mfs in enumerate(mfs_list, 1):
            print(f"MFS {i} :", [cl.label for cl in mfs.clauses])
        print("\n")

        # 3. Génération des combinaisons de clauses à retirer
        cand = XSSGenerator.generate_combinations(mfs_list)
        result_queries = []
        main_clauses_set = set(main_query.clauses)

        # 4. Pour chaque pattern (combinaison de MFS), on retire ces clauses de la requête
        for pattern in cand:
            diff = main_clauses_set - set(pattern.clauses)
            new_query = ConjunctiveQuery()
            new_query.clauses = list(diff)

            # 5. Filtrage pour éviter les sous-requêtes redondantes
            is_sub = False
            to_remove = []
            for idx, existing in enumerate(result_queries):
                existing_set = set(existing.clauses)
                if set(new_query.clauses) <= existing_set:
                    is_sub = True
                    break
                if existing_set <= set(new_query.clauses):
                    to_remove.append(idx)
            if not is_sub:
                for idx in sorted(to_remove, reverse=True):
                    del result_queries[idx]
                result_queries.append(new_query)

        return result_queries


if __name__ == "__main__":
    # Exemple d'utilisation
    endpoint_url = "http://localhost:8000/sparql"
    analyzer = XSSGenerator()

    sparql_query = """
    prefix ub: <http://www.lehigh.edu/~zhp2/2004/0401/univ-bench.owl#>
    select ?x {
      ?x a ub:ResearchGroup;
        ub:subOrganizationOf <http://www.University0.edu>.
    }"""
    devquery=expand_sparql(sparql_query)
    parser = SparqlTripletParser(devquery)
    parser.parse()
    query= parser.query
    print(query.to_sparql())
    # 4️⃣ Exécution de l'analyse des échecs et extraction des MFS
    xss_list = analyzer.compute_xss(query,endpoint_url)
    print(f"Nombre de Xss trouvées : {len(xss_list)}")
    # 5️⃣ Affichage des résultats
    print("\n🔎 Résultat : Minimal Failing Subqueries (MFS)\n")
    for i, mfs in enumerate(xss_list, 1):
        print(f"Xss {i}: {mfs}")
        print(f"- Triplets: {[j.label for j in mfs.clauses]}\n \n")
    print(f"Fin")