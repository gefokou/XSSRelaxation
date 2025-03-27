from rdflib import Graph, URIRef, Literal, Variable
from Query.FilterLiteral import FilterLiteral
from Query.SimpleLiteral import SimpleLiteral

def main():
    # 1. Création d'un graphe avec le même sujet
    g = Graph()
    s = URIRef("http://ex.org/Alice")
    
    g.add((s, URIRef("http://ex.org/age"), Literal(32)))
    g.add((s, URIRef("http://ex.org/name"), Literal("Alice")))

    # 2. Création des clauses
    age_clause = SimpleLiteral((Variable("s"), URIRef("http://ex.org/age"), Variable("age")))
    name_clause = SimpleLiteral((Variable("s"), URIRef("http://ex.org/name"), Variable("name")))

    # 3. Filtre avec syntaxe SPARQL valide
    filt = FilterLiteral("(?age > 30) && (regex(?name, '^A'))")
    filt.add_selected_variables(["age", "name"])

    # 4. Construction de requête valide
    query_str = f"""
    SELECT ?age ?name
    WHERE {{
        {age_clause.get_triple_pattern()}
        {name_clause.get_triple_pattern()}
        FILTER ({filt.filter_expr})
    }}
    """
    
    print("=== Requête finale ===")
    print(query_str)
    
    # 5. Exécution avec gestion d'erreurs
    try:
        results = g.query(query_str)
        print("\n=== Résultats ===")
        for row in results:
            print(f"Age: {row.age}, Nom: {row.name}")
    except Exception as e:
        print(f"\nErreur d'exécution : {str(e)}")

if __name__ == "__main__":
    main()