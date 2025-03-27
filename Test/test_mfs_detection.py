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
# 4️⃣ Exécution de l'analyse des échecs et extraction des MFS
mfs_list = QueryFailureAnalyzer.find_all_failing_causes(query, g)

# 5️⃣ Affichage des résultats
print("\n🔎 Résultat : Minimal Failing Subqueries (MFS)\n")
for i, mfs in enumerate(mfs_list, 1):
    print(f"MFS {i}: {mfs}")
    print(f"- Triplets: {[j.label for j in mfs.clauses]}\n \n")
    print(f"- Triplets: {[j.triple for j in mfs.clauses]}\n \n")
    
