from rdflib import Graph, Namespace, Literal, URIRef, RDF
from Query.ConjunctiveQueryClause import ConjunctiveQuery
from Relaxation.QueryFailureAnalyzer import QueryFailureAnalyzer
from Query.SimpleLiteral import SimpleLiteral
from rdflib.term import Variable

# 1️⃣ Initialisation du graphe RDF
g = Graph()
ex = Namespace("http://example.org/")

# Liaison de l'espace de noms
g.bind("ex", ex)

# Ajout des triplets dans le graphe
g.add((ex.s1, RDF.type, ex.Lecturer))
g.add((ex.s1, ex.teacherOf, Literal("SW")))
g.add((ex.s1, ex.age, Literal(45)))

g.add((ex.s2, RDF.type, ex.Lecturer))
g.add((ex.s2, ex.nationality, Literal("US")))
g.add((ex.s2, ex.age, Literal(46)))

g.add((ex.s3, RDF.type, ex.FullProfessor))
g.add((ex.s3, ex.teacherOf, Literal("DB")))
g.add((ex.s3, ex.age, Literal(46)))

# Sérialisation du graph au format Turtle dans un fichier "graph.ttl"
g.serialize(destination='graph.ttl', format='turtle')