# Create an example conjunctive query Q with some clauses.
from rdflib import Graph, Literal, URIRef, Variable
from Query.ConjunctiveQueryClause import ConjunctiveQuery as Query
from Query.SimpleLiteral import SimpleLiteral
from Relaxation.ParallelXBS import ParallelRelaxationSmartStrategy, ParallelRelaxationStrategy


# 2️⃣ Définition des clauses de la requête
t1 = SimpleLiteral((Variable("p"), URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type"), URIRef("http://example.org/Lecturer")))
t2 = SimpleLiteral((Variable("p"), URIRef("http://example.org/nationality"), Variable("n")))
t3 = SimpleLiteral((Variable("p"), URIRef("http://example.org/teacherOf"), Literal("SW")))
t4 = SimpleLiteral((Variable("p"), URIRef("http://example.org/age"), Literal(46)))

# 3️⃣ Construction de la requête conjonctive
query = Query()
query.add_clause(t1)
query.add_clause(t2)
query.add_clause(t3)
query.add_clause(t4)
query.selected_vars = {"p", "n"}
print(query.to_sparql())

# Create an RDF graph D (can be loaded or built dynamically)
D = Graph()
D.parse("graph.ttl", format="turtle")  # Uncomment if you have a file

# Number of repaired queries needed.
k = 4

# Instantiate the parallel relaxation strategy.
strategy = ParallelRelaxationSmartStrategy(query, D, k)
strategy.parallelxbsv2()

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
for rs in strategy.Res:
    print("results:")
    print("\n")
    print(rs)
    print("\n \n")

print("Statistiques de la methode: \n")
print(f"temps d'execution:{strategy.execution_time}")
print(f"nombre d'execution de requetes:{strategy.query_exec_count}")
# print("Ensemble F:")

# for i in strategy.F:
#     print(i[0].to_sparql())
#     print("\n:")
#     print(i[1].to_sparql())
