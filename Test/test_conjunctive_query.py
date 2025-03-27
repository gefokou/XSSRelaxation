from rdflib import Graph, Namespace, Literal, Variable, URIRef
from rdflib.namespace import RDF
from Query.ConjunctiveQueryClause import ConjunctiveQuery 
from Query.SimpleLiteral import SimpleLiteral
from Query.FilterLiteral import FilterLiteral
# Définition d'un namespace
ex = Namespace("http://example.org/")

# Création du graphe RDF
graph = Graph()

# Ajout de données dans le graphe
graph.add((URIRef("http://example.org/person1"), RDF.type, ex.Human))
graph.add((URIRef("http://example.org/person1"), ex.hasAge, Literal(25)))

graph.add((URIRef("http://example.org/person2"), RDF.type, ex.Human))
graph.add((URIRef("http://example.org/person2"), ex.hasAge, Literal(35)))

graph.add((URIRef("http://example.org/person3"), RDF.type, ex.Human))
graph.add((URIRef("http://example.org/person3"), ex.hasAge, Literal(40)))

# Création des triplets pour la requête
triple1 = SimpleLiteral((Variable("person"), RDF.type, ex.Human))
triple2 = SimpleLiteral((Variable("person"), ex.hasAge, Variable("age")))

# Création du filtre (on veut les humains avec age > 30)
filter_clause = FilterLiteral("?age > 30")

# Création de la requête conjonctive
query = ConjunctiveQuery()
query.add_clause(triple1)
query.add_clause(triple2)
query.add_filter(filter_clause)
query.set_selected_variables(["person", "age"])  # On veut récupérer ?person et ?age

# Affichage de la requête générée
print("🔹 Requête SPARQL générée :")
print(query.to_sparql())

# Exécution de la requête sur le graphe
print("\n🔹 Résultats de la requête :")
results = query.execute(graph)

# Affichage des résultats
for row in results:
    print(f"Personne: {row.person}, Âge: {row.age}")
