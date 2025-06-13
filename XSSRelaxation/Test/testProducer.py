from rdflib import Graph, Literal, URIRef, Variable
from Query.SimpleLiteral import SimpleLiteral
from Relaxation.ParallelXBS import ParallelRelaxationStrategy
from Query.ConjunctiveQueryClause import ConjunctiveQuery

# 2️⃣ Définition des clauses de la requête
t1 = SimpleLiteral((Variable("p"), URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type"), URIRef("http://example.org/Lecturer")))
t2 = SimpleLiteral((Variable("p"), URIRef("http://example.org/nationality"), Variable("n")))
t3 = SimpleLiteral((Variable("p"), URIRef("http://example.org/teacherOf"), Literal("SW")))
t4 = SimpleLiteral((Variable("p"), URIRef("http://example.org/age"), Literal(46)))

# 3️⃣ Construction de la requête conjonctive
query = ConjunctiveQuery()
query.add_clause(t1)
query.add_clause(t2)
query.add_clause(t3)
query.add_clause(t4)
query.selected_vars = {"p", "n"}
print(query.to_sparql())
g= Graph()
g.parse("graph.ttl", format="turtle")

producer = ParallelRelaxationStrategy(query, g, 2)

for i in producer.delta():
    producer.E.put(i)
print(f"Ensemble E:\n")
element = list(producer.E.queue)
for k, j in enumerate(element, 1):
    print(f"{k}:")
    print([i.label for i in j[0].clauses])
    print("-"*50)
producer.producer()

print(f"Candidats produits:\n")
element = list(producer.Cand.queue)
for i in element:
    print(i)