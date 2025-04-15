import math
from rdflib import Graph, URIRef

class SimilarityCalculator:
    def __init__(self, graph: Graph):
        """
        Initialise le calculateur avec un graphe RDF.
        
        :param graph: Un objet rdflib.Graph contenant les données RDF.
        """
        self.g = graph

    def pr_class(self, cls):
        """
        Calcule la probabilité Pr(c) d'une classe c en considérant
        le ratio entre le nombre d'instances de la classe et le total des instances.
        
        :param cls: L'URI de la classe.
        :return: La probabilité de la classe.
        """
        count_cls = len(list(self.g.subjects(predicate=None, object=cls)))
        total_instances = len(set(self.g.subjects()))
        return count_cls / total_instances if total_instances else 0

    def ic_class(self, cls):
        """
        Calcule le contenu informationnel (Information Content) d'une classe.
        
        :param cls: L'URI de la classe.
        :return: La valeur d'information -log(Pr(c)).
        """
        pr = self.pr_class(cls)
        return -math.log(pr) if pr > 0 else 0

    def pr_property(self, prop):
        """
        Calcule la probabilité Pr(p) d'une propriété en
        considérant le ratio entre le nombre de triplets contenant p et le total des triplets.
        
        :param prop: L'URI de la propriété.
        :return: La probabilité de la propriété.
        """
        count_prop = len(list(self.g.triples((None, prop, None))))
        total_triples = len(self.g)
        return count_prop / total_triples if total_triples else 0

    def ic_property(self, prop):
        """
        Calcule le contenu informationnel (Information Content) d'une propriété.
        
        :param prop: L'URI de la propriété.
        :return: La valeur d'information -log(Pr(p)).
        """
        pr = self.pr_property(prop)
        return -math.log(pr) if pr > 0 else 0

    def sim_r1(self, c, c_prime):
        """
        Calcul de la similarité entre deux classes, selon la règle R1 :
        Sim(c, c') = IC(c') / IC(c)
        
        :param c: Classe initiale.
        :param c_prime: Super-classe de c (relaxation).
        :return: La similarité entre les classes.
        """
        ic_c = self.ic_class(c)
        ic_c_prime = self.ic_class(c_prime)
        return ic_c_prime / ic_c if ic_c > 0 else 0

    def sim_r2(self, p, p_prime):
        """
        Calcul de la similarité entre deux propriétés, selon la règle R2 :
        Sim(p, p') = IC(p') / IC(p)
        
        :param p: Propriété initiale.
        :param p_prime: Super-propriété de p (relaxation).
        :return: La similarité entre les propriétés.
        """
        ic_p = self.ic_property(p)
        ic_p_prime = self.ic_property(p_prime)
        return ic_p_prime / ic_p if ic_p > 0 else 0

    def sim_r3(self, const, variable):
        """
        Pour la règle R3, qui remplace une constante par une variable,
        la similarité est définie comme nulle.
        
        :param const: La constante initiale.
        :param variable: La variable relaxée.
        :return: 0, car la similarité est nulle.
        """
        return 0

    def sim_triple(self, t, t_prime, rule_applied):
        """
        Calcule la similarité globale entre deux triplets t et t' obtenus par relaxation
        selon l'une des règles R1, R2 ou R3.
        
        La similarité globale se calcule comme la moyenne des similarités des sujets,
        prédicats et objets.
        
        :param t: Le triplet initial (s, p, o).
        :param t_prime: Le triplet relaxé (s', p', o').
        :param rule_applied: La règle de relaxation utilisée ('R1', 'R2' ou 'R3').
        :return: Une valeur de similarité entre 0 et 1.
        """
        s, p, o = t
        s_p, p_p, o_p = t_prime

        if rule_applied == 'R1':
            sim_s = self.sim_r1(s, s_p)
            sim_p = 1  # Le prédicat reste inchangé
            sim_o = 1  # L'objet reste inchangé
        elif rule_applied == 'R2':
            sim_s = 1  # Le sujet reste inchangé
            sim_p = self.sim_r2(p, p_p)
            sim_o = 1  # L'objet reste inchangé
        elif rule_applied == 'R3':
            # Pour R3, si l'élément relaxé est une variable (représentée par un ? en chaîne)
            sim_s = 0 if isinstance(s_p, str) and s_p.startswith("?") else 1
            sim_p = 0 if isinstance(p_p, str) and p_p.startswith("?") else 1
            sim_o = 0 if isinstance(o_p, str) and o_p.startswith("?") else 1
        else:
            sim_s = sim_p = sim_o = 0

        return (sim_s + sim_p + sim_o) / 3

# --- Exemple d'utilisation ---

# Création du graphe RDF
g = Graph()
# Charger le graphe RDF à partir d'un fichier (ajuster le chemin et le format selon vos données)
# g.parse("chemin/vers/ton_fichier.rdf", format="xml")

# Instanciation du calculateur avec le graphe
sim_calc = SimilarityCalculator(g)

# Définition de deux triplets pour l'exemple.
# t est le triplet initial et t_prime est le triplet relaxé.
t = (
    URIRef("http://example.org#Student"), 
    URIRef("http://example.org#teaches"), 
    URIRef("http://example.org#Course")
)
t_prime = (
    URIRef("http://example.org#Person"),  # Relaxation de la classe "Student" vers la super-classe "Person" (R1)
    URIRef("http://example.org#teaches"), 
    URIRef("http://example.org#Course")
)

# Calcul de la similarité en appliquant la règle R1
similarity = sim_calc.sim_triple(t, t_prime, rule_applied='R1')
print("Similarity:", similarity)
