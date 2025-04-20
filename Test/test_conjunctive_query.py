from rdflib import XSD, Graph, Namespace, Literal, Variable, URIRef
from rdflib.namespace import RDF
from Query.ConjunctiveQueryClause import ConjunctiveQuery 
from Query.SimpleLiteral import SimpleLiteral
from Query.FilterLiteral import FilterLiteral
# Définition d'un namespace
ex = Namespace("http://example.org/")

# Création du graphe RDF
graph = Graph()
graph.parse("graph.ttl", format="turtle")  # Charger le graphe à partir d'un fichier Turtle

t1 = SimpleLiteral((Variable("p"), URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type"), URIRef("http://example.org/Lecturer")))
t2 = SimpleLiteral((Variable("p"), URIRef("http://example.org/nationality"), Variable("n")))
t3 = SimpleLiteral((Variable("p"), URIRef("http://example.org/teacherOf"), Literal("SW")))
t4 = SimpleLiteral((Variable("p"), URIRef("http://example.org/age"), Literal(46, datatype=XSD.integer)))

# 3️⃣ Construction de la requête conjonctive
query = ConjunctiveQuery()
query.add_clause(t1)
query.add_clause(t2)
query.add_clause(t3)
query.add_clause(t4)
query.selected_vars = {"p", "n"}
# query.add_filter(filter_clause)
# On veut récupérer ?person et ?age

# Affichage de la requête générée
print("🔹 Requête SPARQL générée :")
print(query.to_sparql())

# Exécution de la requête sur le graphe
print("\n🔹 Résultats de la requête :")
results = query.execute(graph)

# Affichage des résultats
for row in results:
    print(row.bindings)
