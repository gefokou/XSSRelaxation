from rdflib import Graph, Namespace, URIRef, Literal, RDF
from Query.ConjunctiveQueryClause import ConjunctiveQuery
from Relaxation.ConjunctiveQueryTools import ConjunctiveQueryTools
from Relaxation.QuerySuccessful import QuerySuccessful
from Query.SimpleLiteral import SimpleLiteral
from rdflib.term import Variable

# 1️⃣ Chargement du graphe RDF
g = Graph()
ex = Namespace("http://example.org/")
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

# 2️⃣ Définition de la requête conjonctive
t1 = SimpleLiteral((Variable("p"), URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type"), URIRef("http://example.org/Lecturer")))
t2 = SimpleLiteral((Variable("p"), URIRef("http://example.org/nationality"), Variable("n")))
t3 = SimpleLiteral((Variable("p"), URIRef("http://example.org/teacherOf"), Literal("SW")))
t4 = SimpleLiteral((Variable("p"), URIRef("http://example.org/age"), Literal(46)))

# Création de la requête conjonctive
query = ConjunctiveQuery()
query.add_clause(t1)
query.add_clause(t2)
query.add_clause(t3)
query.add_clause(t4)
query.selected_vars = {"p", "n"}

# 3️⃣ Exécution de la relaxation (XSS) sur la requête
nbr_answers = 1  # Nombre minimum de réponses attendues
relaxed_queries = QuerySuccessful.find_all_success_queries(query, g, nbr_answers)

# 4️⃣ Affichage des résultats
print("\n🔹XSS trouvées:")
print(relaxed_queries)
for i, relaxed_query in enumerate(relaxed_queries, 1):
    print(f"✅ Relaxation {i} :\n{relaxed_query.to_sparql()}\n")
