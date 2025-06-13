from SPARQLWrapper import SPARQLWrapper, JSON

# Endpoint SPARQL du serveur local
sparql = SPARQLWrapper("http://localhost:8000")  # ou http://localhost:8000 selon le moteur
sparql.setReturnFormat(JSON)

# Requête SELECT (préfixe et URIs selon le schéma LUBM)
sparql.setQuery("""
    PREFIX ub: <http://www.lehigh.edu/~zhp2/2004/0401/univ-bench.owl#>
    SELECT ?student ?course WHERE {
        ?student ?a ?course.
    }
""")

results = sparql.query().convert()
for result in results["results"]["bindings"]:
    print(result["student"]["value"], "->", result["course"]["value"])
