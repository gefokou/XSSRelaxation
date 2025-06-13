from rdflib import Graph
from rdflib.plugins.sparql import prepareQuery

graph = Graph()
graph.parse("Experimentation/univ-bench.owl")

query="""
    PREFIX ub: <http://www.lehigh.edu/~zhp2/2004/0401/univ-bench.owl#>
    SELECT ?student ?course WHERE {
        ?student ?a ?course.
    }
"""
query2 = prepareQuery(query)
results = graph.query(query2)

print("🔹 Résultats de la requête :")
for row in results:
    print(row)