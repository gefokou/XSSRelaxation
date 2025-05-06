from SPARQLWrapper import SPARQLWrapper, JSON

# Configurer la connexion à l'endpoint local
sparql = SPARQLWrapper("http://localhost:8000/sparql")

# Définir la requête SPARQL
sparql.setQuery("""
prefix ub: <http://www.lehigh.edu/~zhp2/2004/0401/univ-bench.owl#>
select ?x {
  ?x a ub:GraduateStudent;
    ub:takesCourse <http://www.Department0.University0.edu/GraduateCourse0>.
}
""")

# Spécifier le format de retour (JSON)
sparql.setReturnFormat(JSON)

# Exécuter la requête et obtenir les résultats
results = sparql.query().convert()

# Afficher les résultats
for result in results["results"]["bindings"]:
    print(result)