# test_simple_literal.py
from rdflib import Graph, Variable, URIRef, Literal

# Assurez-vous que l'import correspond à votre structure de fichiers
from Query.SimpleLiteral import SimpleLiteral

def main():
    # 1. Création d'un triplet de test
    triple = (
        Variable("s"),
        URIRef("http://example.org/hasName"),
        Variable("name")
    )
    
    # 2. Instanciation de la clause
    clause = SimpleLiteral(triple)
    
    # 3. Sélection des variables
    clause.add_selected_variables(["s", "name"])
    
    # 4. Affichage de la clause
    print("Clause créée :")
    print(f"Triplet : {clause.triple}")
    print(f"Triplet : {clause.label}")
    print(f"Variables mentionnées : {clause.mentioned_vars}")
    print(f"Variables sélectionnées : {clause.selected_vars}")
    print(f"Clause SPARQL générée :\n{clause.to_sparql()}\n")
    
    # 5. Création d'un graphe de test
    g = Graph()
    g.add((
        URIRef("http://example.org/Alice"),
        URIRef("http://example.org/hasName"),
        Literal("Alice")
    ))
    g.add((
        URIRef("http://example.org/Bob"),
        URIRef("http://example.org/hasName"),
        Literal("Bob")
    ))
    
    # 6. Exécution de la requête
    print("Résultats de la requête :")
    results = clause.execute(g)
    for row in results:
        print(f"Subject: {row.s}, Name: {row.name}")

if __name__ == "__main__":
    main()