# Create an example conjunctive query Q with some clauses.

from Relaxation.EndpointMode.ParallelXBs import ParallelRelaxationStrategy
from Relaxation.parser import SparqlTripletParser
from Relaxation.parser2 import expand_sparql

# # 2️⃣ Définition des clauses de la requête
# t1 = SimpleLiteral((Variable("p"), URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type"), URIRef("http://example.org/Lecturer")))
# t2 = SimpleLiteral((Variable("p"), URIRef("http://example.org/nationality"), Variable("n")))
# t3 = SimpleLiteral((Variable("p"), URIRef("http://example.org/teacherOf"), Literal("SW")))
# t4 = SimpleLiteral((Variable("p"), URIRef("http://example.org/age"), Literal(46)))

# # 3️⃣ Construction de la requête conjonctive
# query = Query()
# query.add_clause(t1)
# query.add_clause(t2)
# query.add_clause(t3)
# query.add_clause(t4)
# query.selected_vars = {"p", "n"}
# print(query.to_sparql())

sparql_query = """
PREFIX ub: <http://www.lehigh.edu/~zhp2/2004/0401/univ-bench.owl#>
SELECT *
WHERE { 
    <http://www.Department0.University0.edu/UndergraduateStudent33> ub:advisor ?Y1 . 
    ?Y1 ub:doctoralDegreeFrom ?Y2 .
    ?Y2 ub:hasAlumnus ?Y3 .
    ?Y3 ub:title ?Y4 .
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
D = "http://localhost:3030/ds/sparql"
 # Uncomment if you have a file

# Number of repaired queries needed.


# Instantiate the parallel relaxation strategy.
strategy = ParallelRelaxationStrategy(query, D, k=40)
strategy.parallelxbs()

print("Requetes reparées:")
print("\n")
for rq in strategy.Req:
    print(rq[0].to_sparql())
    print("\n")
    print(f"similarity: {rq[1]}")
    print("\n \n")

print("\n \n")

# Afficher le contenu de Res 
print("Resultats obtenus:")
print("\n")
# for rs in strategy.Res:
#     print("results:")
#     print("\n")
#     print(rs)
#     print("\n \n")

print("Statistiques de la methode: \n")
print(f"temps d'execution:{strategy.execution_time}")
print(f"nombre d'execution de requetes:{strategy.query_exec_count}")
print("nombre de resultats:",len(strategy.Res))