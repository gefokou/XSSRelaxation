import math
from SPARQLWrapper import SPARQLWrapper, JSON
from rdflib import BNode, URIRef, Variable

from Relaxation.parser import SparqlTripletParser
from Relaxation.parser2 import expand_sparql

class SimilarityCalculator:
    def __init__(self, endpoint_url: str):
        """
        Initialise le calculateur avec l'URL d'un endpoint SPARQL.

        :param endpoint_url: URL du endpoint SPARQL.
        """
        self.endpoint = SPARQLWrapper(endpoint_url)
        self.endpoint.setReturnFormat(JSON)

    def pr_class(self, cls_uri):
        """
        Calcule la probabilité qu'une instance soit de type `cls_uri`.
        Cette probabilité est estimée par :
        (# d'instances de la classe) / (nombre total d'instances)
        où une instance est toute ressource apparaissant comme sujet dans un triplet.
        """
        # 1. Construire la requête SPARQL pour compter distinctement les sujets de type cls_uri
        query = f"""
        SELECT (COUNT(DISTINCT ?s) AS ?count) WHERE {{
            ?s a <{cls_uri}> .
        }}
        """
        # On envoie cette requête à l'endpoint SPARQL
        self.endpoint.setQuery(query)
        # On exécute la requête et récupère le résultat au format JSON
        results = self.endpoint.query().convert()
        # On extrait la valeur du binding "count" (chaîne de caractères) et on la convertit en int
        count_cls = int(results["results"]["bindings"][0]["count"]["value"])

        # 2. Construire la requête SPARQL pour compter le nombre total d'instances
        #    On considère ici qu'une instance est tout sujet ?s apparaissant dans un triplet quelconque.
        total_query = """
        SELECT (COUNT(DISTINCT ?s) AS ?total) WHERE {
            ?s a ?o .
        }
        """
        self.endpoint.setQuery(total_query)
        results = self.endpoint.query().convert()
        total_instances = int(results["results"]["bindings"][0]["total"]["value"])

        # 3. Retourner la fraction : nombre d'instances de la classe / nombre total d'instances
        #    Si le graphe est vide (total_instances == 0), on retourne 0 pour éviter division par zéro.
        return count_cls / total_instances if total_instances else 0


    def ic_class(self, cls):
        pr = self.pr_class(cls)
        return -math.log(pr) if pr > 0 else 0


    def pr_property(self, prop_uri):
        """
        Calcule la probabilité d'occurrence du prédicat `prop_uri`.
        Cette probabilité est estimée par :
        (# de triplets utilisant ce prédicat) / (nombre total de triplets)
        """
        # 1. Construire la requête SPARQL pour compter tous les triplets où ?s prop_uri ?o
        query = f"""
        SELECT (COUNT(?s) AS ?count) WHERE {{
            ?s <{prop_uri}> ?o .
        }}
        """
        self.endpoint.setQuery(query)
        results = self.endpoint.query().convert()
        count_prop = int(results["results"]["bindings"][0]["count"]["value"])

        # 2. Construire la requête SPARQL pour compter le nombre total de triplets
        #    COUNT(*) compte toutes les lignes du pattern { ?s ?p ?o }.
        total_query = """
        SELECT (COUNT(*) AS ?total) WHERE {
            ?s ?p ?o .
        }
        """
        self.endpoint.setQuery(total_query)
        results = self.endpoint.query().convert()
        total_triples = int(results["results"]["bindings"][0]["total"]["value"])

        # 3. Retourner la fraction : occurrences du prédicat / total des triplets
        #    Si le graphe est vide (total_triples == 0), on retourne 0.
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
        if len(query) != len(relaxed_query):
            raise ValueError("Les requêtes doivent contenir le même nombre de patrons de triplet.")
        sim_values = [
            self.sim_triple(t.triple, t_prime.triple)
            for t, t_prime in zip(query, relaxed_query)
        ]
        return sum(sim_values) / len(sim_values) if sim_values else 0


# --------------------
# Test de base
# --------------------
if __name__ == "__main__":
    # Endpoint de test (ajuster l'URL si besoin)
    endpoint = "http://localhost:8000/sparql"
    sim = SimilarityCalculator(endpoint)
    sparql_query = """
    prefix ub: <http://www.lehigh.edu/~zhp2/2004/0401/univ-bench.owl#>
    select ?x {
      ?x a ub:ResearchGroup;
        ub:subOrganizationOf <http://www.University0.edu>.
    }"""
    devquery=expand_sparql(sparql_query)
    parser = SparqlTripletParser(devquery)
    parser.parse()
    query= parser.query

    sparql_queryp = """
    prefix ub: <http://www.lehigh.edu/~zhp2/2004/0401/univ-bench.owl#>
    select ?x {
      ?x a ub:ResearchGroup;
        ub:subOrganizationOf ?y.
    }"""
    devqueryp=expand_sparql(sparql_queryp)
    parser2 = SparqlTripletParser(devqueryp)
    parser2.parse()
    queryp= parser2.query

    similarite=sim.query_similarity(query.clauses, queryp.clauses)
    print(f"Similarité entre les requêtes : {similarite}")
