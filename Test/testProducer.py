from rdflib import Graph, URIRef, Variable
from Query.SimpleLiteral import SimpleLiteral
from Relaxation.ParallelXBS import ParallelRelaxationStrategy
from Query.ConjunctiveQueryClause import ConjunctiveQuery

query = ConjunctiveQuery()
query.add_clause(SimpleLiteral((Variable("p"), URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type"), URIRef("http://example.org/Lecturer"))))

g= Graph()
g.parse("graph.ttl", format="turtle")

producer = ParallelRelaxationStrategy(query, g, 2)
for i in producer.delta():
    producer.E.put(i)
producer.producer()
