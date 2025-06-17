import math
from rdflib import RDF, BNode, Graph, Literal, URIRef, Variable
from Query.ConjunctiveQueryClause import ConjunctiveQuery
from Query.SimpleLiteral import SimpleLiteral
# from Relaxation.relaxtools import ConjunctiveQueryRelaxation

class SimilarityCalculator:
    def __init__(self, graph: Graph):
        """
        Initialise le calculateur avec un graphe RDF.
        
        :param graph: Un objet rdflib.Graph contenant les données RDF.
        """
        self.g = graph

    def pr_class(self, cls):
        count_cls = len(list(self.g.subjects(predicate=RDF.type, object=cls)))
        total_instances = len(set(self.g.subjects(predicate=RDF.type)))
        return count_cls / total_instances if total_instances else 0

    def ic_class(self, cls):
        pr = self.pr_class(cls)
        return -math.log(pr) if pr > 0 else 0

    def pr_property(self, prop):
        count_prop = len(list(self.g.triples((None, prop, None))))
        total_triples = len(self.g)
        return count_prop / total_triples if total_triples else 0

    def ic_property(self, prop):
        pr = self.pr_property(prop)
        return -math.log(pr) if pr > 0 else 0

    def sim_r1(self, c, c_prime):
        ic_c = self.ic_class(c)
        ic_c_prime = self.ic_class(c_prime)
        return ic_c_prime / ic_c if ic_c > 0 else 0

    def sim_r2(self, p, p_prime):
        ic_p = self.ic_property(p)
        ic_p_prime = self.ic_property(p_prime)
        return ic_p_prime / ic_p if ic_p > 0 else 0

    def sim_r3(self, const, variable):
        return 0

    def sim_element(self, original, relaxed, element_type: str):
        """
        Calcule la similarité pour une composante donnée d'un triplet.
        """
        
        if original == relaxed:
            return 1
        if isinstance(relaxed, Variable):
            return 0
        if isinstance(relaxed, BNode):
            return -0.5
        if element_type in ['subject', 'object']:
            return self.sim_r1(original, relaxed)
        if element_type == 'predicate':
            return self.sim_r2(original, relaxed)
        return 0

    def sim_triple(self, t, t_prime):
        """
        Calcule la similarité globale entre deux triplets en utilisant une approche
        générique qui détermine pour chaque composante la fonction de similarité à appliquer.
        """
        element_types = ['subject', 'predicate', 'object']
        sim_values = [
            self.sim_element(orig, relax, etype)
            for orig, relax, etype in zip(t, t_prime, element_types)
        ]
        return sum(sim_values) / len(sim_values)
    
    def query_similarity(self, query, relaxed_query):
        """
        Calcule la similarité globale entre deux requêtes conjonctives.
        Chaque requête est représentée par une liste de triplets (patrons),
        et la similarité globale est la moyenne des similarités calculées sur 
        chaque patron de triplet correspondant.
        
        :param g: Le graphe RDF utilisé dans les calculs.
        :param query: La requête initiale représentée par une liste de triplets (s, p, o).
        :param relaxed_query: La requête relaxée, sous forme d'une liste de triplets correspondants.
        :return: La similarité globale (une valeur entre 0 et 1) entre les deux requêtes.
        """
        list_match=[]
        if len(query) != len(relaxed_query):
            raise ValueError("Les requêtes doivent contenir le même nombre de patrons de triplet.")
        for i in query:
            for j in relaxed_query:
                if i.label in j.label:
                    list_match.append((i,j))
        # print(list_match)
        sim_values = [
            self.sim_triple(t.triple, t_prime.triple)
            for (t, t_prime) in list_match
        ]
        return sum(sim_values) / len(sim_values) if sim_values else 0
        
    def query_similarity2(self, query, relaxed_query):
        """
        Calcule la similarité globale entre deux requêtes conjonctives.
        Chaque requête est représentée par une liste de triplets (patrons),
        et la similarité globale est la moyenne des similarités calculées sur 
        chaque patron de triplet correspondant.
        
        :param g: Le graphe RDF utilisé dans les calculs.
        :param query: La requête initiale représentée par une liste de triplets (s, p, o).
        :param relaxed_query: La requête relaxée, sous forme d'une liste de triplets correspondants.
        :return: La similarité globale (une valeur entre 0 et 1) entre les deux requêtes.
        """
        if len(query) != len(relaxed_query):
            raise ValueError("Les requêtes doivent contenir le même nombre de patrons de triplet.")
        
        sim_values = [
            self.sim_triple(t.triple, t_prime.triple)
            for t, t_prime in zip(query, relaxed_query)
        ]
        return sum(sim_values) / len(sim_values) if sim_values else 0

# --- Exemple d'utilisation ---
# if __name__ == "__main__":
#     # Création du graphe RDF
#     g = Graph()
#     g.parse("graph.ttl", format="turtle")  # Chargez vos données RDF

#     # Instanciation du calculateur avec le graphe
#     sim_calc = SimilarityCalculator(g)

#     # Définition d'un triplet initial et d'un triplet relaxé
#     t1= SimpleLiteral((Variable("p"), URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type"), URIRef("http://example.org/Lecturer")))
#     t1_prime = SimpleLiteral((Variable("p"), URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type"), Variable("s")))
#     t2 = SimpleLiteral((Variable("p"), URIRef("http://example.org/teacherOf"), Literal("SW")))
#     t2_prime = SimpleLiteral((Variable("p"), URIRef("http://example.org/teacherOf"), Variable("c")))

#     q=ConjunctiveQuery()
#     q.add_clause(t1)
#     q.add_clause(t2)

#     q_prime=ConjunctiveQuery()
#     q_prime.add_clause(t1_prime)
#     q_prime.add_clause(t2)
    
#     cqr = ConjunctiveQueryRelaxation(q, g, order=1)
#     relaxed_versions = cqr.relax_query()
#     # Calcul de la similarité entre les deux triplets
#     for i in relaxed_versions[0]:
#         similarity = sim_calc.query_similarity(q.clauses, i.clauses)

#         # Affichage du résultat
#         print("Similarité entre les requêtes :")
#         print("Requête originale:", q.to_sparql())
#         print("Requête relaxée:", i.to_sparql())

#         print("Similarity:", similarity)
