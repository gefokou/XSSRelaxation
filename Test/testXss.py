from rdflib import Graph, Namespace, Literal, URIRef, RDF
from Query.ConjunctiveQueryClause import ConjunctiveQuery
from Relaxation.QueryFailureAnalyzer import QueryFailureAnalyzer
from Query.SimpleLiteral import SimpleLiteral
from rdflib.term import Variable

from Relaxation.XSSGenerator import XSSGenerator

# 1️⃣ Initialisation du graphe RDF
# 1️⃣ Initialisation du graphe RDF
g = Graph()
g.parse("graph.ttl", format="turtle")

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

# # 5️⃣ Affichage des résultats
print("\n🔎 Résultat : Minimal Failing Subqueries (MFS)\n")
for i, mfs in enumerate(mfs_list, 1):
    print(f"MFS {i}: {mfs}")
    print(f"- Triplets: {[j.label for j in mfs.clauses]}\n \n")
#     print(f"- Triplets: {[j.triple for j in mfs.clauses]}\n \n")
print(mfs_list)
combined_ex1 =XSSGenerator.generate_combinations(mfs_list)
print("Exemple 1 - Combinaisons obtenues:")
for comb in combined_ex1:
    # # Affichage en triant les triplets selon leur littéral pour une lecture claire
    # sorted_comb = sorted(comb, key=lambda triple: str(triple[2]))
    # # On concatène les littéraux pour simuler t1t2, etc.
    print("".join(str(triple.label) for triple in comb.clauses))
# Calcul des XSS
xss_results = XSSGenerator.compute_xss(query, mfs_list)

# Affichage des résultats
print(f"Nombre de XSS trouvés : {len(xss_results)}")
for i, xss in enumerate(xss_results, 1):
    print(f"XSS {i}:")
    print([j.label for j in xss.clauses])
    print("-"*50)
