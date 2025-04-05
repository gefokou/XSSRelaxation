import rdflib
from rdflib import Graph, URIRef, Literal, Variable
from Query.SimpleLiteral import SimpleLiteral
from rdflib import URIRef, RDFS

# ---------------------------
# Constantes et compteurs globaux
# ---------------------------
SUPPRESS_NODE_LEVEL = -1    # Niveau de relaxation pour la suppression d'un nœud
LEVEL_ORDER = 0             # Ordre de relaxation par niveau
SIM_ORDER = 1               # Ordre de relaxation par similarité
HYBRID_ORDER = 2            # Ordre hybride

num_resource_release = 0    # Compteur pour générer des variables de ressources
num_pred_release = 0        # Compteur pour générer des variables de prédicat

# ---------------------------
# Fonctions dummy pour la similarité et récupération de super classes/propriétés
# ---------------------------
def similarity_measure_class(original_node, relaxed_node):
    """
    Simule le calcul d'une mesure de similarité entre deux nœuds pour les sujets/objets.
    """
    return 0.9  # Valeur constante pour la démonstration

def similarity_measure_property(original_node, relaxed_node):
    """
    Simule le calcul d'une mesure de similarité pour les prédicats.
    """
    return 0.9  # Valeur constante pour la démonstration

def get_super_classes(uri):
    """
    Simule la récupération des super-classes pour un URI.
    Retourne un dictionnaire {alternative_node: niveau_relaxation}.
    """
    if isinstance(uri, URIRef):
        # Exemple : remplace "A" par "SuperA" dans l'URI
        super_uri = URIRef(str(uri).replace("A", "SuperA"))
        return {super_uri: 1}
    return {}

def get_super_classes(uri, graph):
    """
    Pour un URI donné, interroge le graphe pour obtenir toutes les super-classes 
    (triplets de la forme (uri, RDFS.subClassOf, super_class)).
    
    Args:
        uri (URIRef): Le nœud pour lequel on souhaite récupérer les super-classes.
        graph (rdflib.Graph): Le graphe RDF dans lequel effectuer la recherche.
        
    Returns:
        dict: Un dictionnaire où les clés sont les super-classes (URIRef) et la valeur associée est un niveau de relaxation (ici fixé à 1).
              Si aucune super-classe n'est trouvée, un comportement par défaut est appliqué.
    """
    # Vérifier que uri est bien une URI
    if not isinstance(uri, URIRef):
        return {}

    super_classes = {}
    
    # Recherche dans le graphe des triplets (uri, RDFS.subClassOf, ?super)
    for _, _, super_class in graph.triples((uri, RDFS.subClassOf, None)):
        super_classes[super_class] = 1

    # Si aucune super-classe n'est trouvée dans le graphe, on applique un comportement par défaut
    if not super_classes:
        # Par exemple, transformer "P" en "SuperP" dans l'URI, comme comportement par défaut
        default_super = URIRef(str(uri).replace("P", "SuperP"))
        super_classes[default_super] = 1

    return super_classes

def get_super_properties(uri, graph):
    """
    Pour un URI donné, interroge le graphe pour obtenir toutes les super-propriétés 
    (triplets de la forme (uri, RDFS.subPropertyOf, super_property)).
    
    Args:
        uri (URIRef): Le nœud pour lequel on souhaite récupérer les super-propriétés.
        graph (rdflib.Graph): Le graphe RDF dans lequel effectuer la recherche.
        
    Returns:
        dict: Un dictionnaire où les clés sont les super-propriétés (URIRef) et la valeur associée est un niveau de relaxation (ici fixé à 1).
              Si aucune super-propriété n'est trouvée, un comportement par défaut est appliqué.
    """
    # Vérifier que uri est bien une URI
    if not isinstance(uri, URIRef):
        return {}

    super_properties = {}
    
    # Recherche dans le graphe des triplets (uri, RDFS.subPropertyOf, ?super)
    for _, _, super_property in graph.triples((uri, RDFS.subPropertyOf, None)):
        super_properties[super_property] = 1

    # Si aucune super-propriété n'est trouvée dans le graphe, on applique un comportement par défaut
    if not super_properties:
        # Par exemple, transformer "P" en "SuperP" dans l'URI, comme comportement par défaut
        default_super = URIRef(str(uri).replace("P", "SuperP"))
        super_properties[default_super] = 1

    return super_properties
    """
    Pour un URI donné, interroge le graphe pour obtenir toutes les super-classes 
    (triplets de la forme (uri, RDFS.subClassOf, super_class)).
    
    Args:
        uri (URIRef): Le nœud pour lequel on souhaite récupérer les super-classes.
        graph (rdflib.Graph): Le graphe RDF dans lequel effectuer la recherche.
        
    Returns:
        dict: Un dictionnaire où les clés sont les super-classes (URIRef) et la valeur associée est un niveau de relaxation (ici fixé à 1).
              Si aucune super-classe n'est trouvée, un comportement par défaut est appliqué.
    """
    # Vérifier que uri est bien une URI
    if not isinstance(uri, URIRef):
        return {}

    super_classes = {}
    
    # Recherche dans le graphe des triplets (uri, RDFS.subClassOf, ?super)
    for _, _, super_class in graph.triples((uri, RDFS.subClassOf, None)):
        super_classes[super_class] = 1

    # Si aucune super-classe n'est trouvée dans le graphe, on applique un comportement par défaut
    if not super_classes:
        # Par exemple, transformer "P" en "SuperP" dans l'URI, comme comportement par défaut
        default_super = URIRef(str(uri).replace("P", "SuperP"))
        super_classes[default_super] = 1

    return super_classes


# ---------------------------
# Classe représentant un triplet relaxé
# ---------------------------
class NodeRelaxed:
    def __init__(self, node_1, node_2, node_3, similarity, relaxation_levels):
        """
        node_1 : sujet (subject)
        node_2 : prédicat (predicate)
        node_3 : objet (object)
        similarity : score de similarité (float)
        relaxation_levels : liste d'entiers indiquant le niveau de relaxation pour chaque composante
        """
        self.node_1 = node_1
        self.node_2 = node_2
        self.node_3 = node_3
        self.similarity = similarity
        self.relaxation_levels = relaxation_levels

    @staticmethod
    def merge(relax_s, relax_p, relax_o):
        """
        Fusionne trois relaxations (pour sujet, prédicat et objet) en une nouvelle relaxation.
        Ici, on calcule la similarité moyenne et on combine les niveaux de relaxation.
        """
        sim = (relax_s.similarity + relax_p.similarity + relax_o.similarity) / 3.0
        # On combine les niveaux de relaxation (pour simplifier, on prend le premier niveau de chaque)
        levels = [relax_s.relaxation_levels[0], relax_p.relaxation_levels[1], relax_o.relaxation_levels[2]]
        return NodeRelaxed(relax_s.node_1, relax_p.node_2, relax_o.node_3, sim, levels)

    def get_relaxation_level(self):
        """
        Retourne une valeur indicative de l'ampleur de la relaxation (ici la somme des niveaux).
        """
        return sum(self.relaxation_levels)

    def __repr__(self):
        return f"NodeRelaxed({self.node_1}, {self.node_2}, {self.node_3}, sim={self.similarity}, levels={self.relaxation_levels})"
# ---------------------------
# Classe principale de relaxation de triplet
# ---------------------------
class TripleRelaxation:
    def __init__(self, clause, session, order=SIM_ORDER):
        """
        clause : Un triplet RDF sous forme de tuple (sujet, prédicat, objet) utilisant rdflib.
        session : Contexte d'exécution (ici utilisé pour simuler des mesures de similarité).
        order : Mode d'ordonnancement de la relaxation (SIM_ORDER par défaut).
        """
        global num_resource_release, num_pred_release
        self.session = session
        self.current_clause = clause  # Le triplet d'origine
        self.relaxation_order = order
        self.subject_var = None
        self.object_var = None
        self.predicat_var = None
        self.relaxed_subject = []
        self.relaxed_predicat = []
        self.relaxed_object = []
        self.relaxed_triple = []
        self.current_elt = -1  # Indice courant pour l'itération

        # Exécute la relaxation sur le triplet
        self.triple_relaxation(clause)

    def relax_node(self, original_node):
        """
        Relaxation d'un nœud (sujet ou objet).
        Retourne un dictionnaire {nœud_alternative: niveau_relaxation}.
        """
        global num_resource_release
        relaxed_node = {}
        if isinstance(original_node, URIRef):
            relaxed_node[original_node] = 0
            relaxed_node.update(get_super_classes(original_node, self.session))
            var_name = f"R{num_resource_release}"
            num_resource_release += 1
            var_node = Variable(var_name)
            relaxed_node[var_node] = SUPPRESS_NODE_LEVEL
        elif isinstance(original_node, Literal):
            relaxed_node[original_node] = 0
            var_name = f"R{num_resource_release}"
            num_resource_release += 1
            var_node = Variable(var_name)
            relaxed_node[var_node] = SUPPRESS_NODE_LEVEL
        else:
            relaxed_node[original_node] = 0
        return relaxed_node

    def relax_predicate(self, original_node):
        """
        Relaxation d'un prédicat.
        Retourne un dictionnaire {nœud_alternative: niveau_relaxation}.
        """
        global num_pred_release
        relaxed_node = {}
        if isinstance(original_node, URIRef):
            relaxed_node[original_node] = 0
            relaxed_node.update(get_super_properties(original_node,self.session))
            var_name = f"P{num_pred_release}"
            num_pred_release += 1
            var_node = Variable(var_name)
            relaxed_node[var_node] = SUPPRESS_NODE_LEVEL
        elif isinstance(original_node, Literal):
            relaxed_node[original_node] = 0
            var_name = f"P{num_pred_release}"
            num_pred_release += 1
            var_node = Variable(var_name)
            relaxed_node[var_node] = SUPPRESS_NODE_LEVEL
        else:
            relaxed_node[original_node] = 0
        return relaxed_node

    def triple_relaxation(self, clause):
        """
        Applique la relaxation sur le triplet (clause).
        clause : tuple (sujet, prédicat, objet).
        """
        subject, predicate, obj = clause.triple

        # Relaxation du sujet
        if isinstance(subject, URIRef):
            self.relaxed_subject = []
            subj_relax = self.relax_node(subject)
            for node, level in subj_relax.items():
                sim = similarity_measure_class(subject, node) / 3.0
                # On initialise le NodeRelaxed pour le sujet (les autres composantes sont None pour l'instant)
                self.relaxed_subject.append(NodeRelaxed(node, None, None, sim, [level, -2, -2]))
        else:
            self.subject_var = subject

        # Relaxation de l'objet
        if isinstance(obj, URIRef):
            self.relaxed_object = []
            obj_relax = self.relax_node(obj)
            for node, level in obj_relax.items():
                sim = similarity_measure_class(obj, node) / 3.0
                self.relaxed_object.append(NodeRelaxed(None, None, node, sim, [-2, -2, level]))
        else:
            self.object_var = obj

        # Relaxation du prédicat
        if predicate is not None:
            if isinstance(predicate, URIRef):
                self.relaxed_predicat = []
                pred_relax = self.relax_predicate(predicate)
                for node, level in pred_relax.items():
                    sim = similarity_measure_property(predicate, node) / 3.0
                    self.relaxed_predicat.append(NodeRelaxed(None, node, None, sim, [-2, level, -2]))
            else:
                self.predicat_var = predicate

        # Combine les relaxations des différents nœuds en relaxations de triplets
        self.all_triple_relaxation()

    def all_triple_relaxation(self):
        """
        Génère toutes les combinaisons possibles de triplets relaxés à partir
        des relaxations des sujets, prédicats et objets.
        """
        self.relaxed_triple = []
        if self.relaxed_subject:
            if self.relaxed_predicat:
                # Utilise l'objet original (sous forme de variable si nécessaire)
                obj_node = self.object_var if self.object_var is not None else None
                dummy_obj = NodeRelaxed(None, None, obj_node, 1.0/3, [-2, -2, 0])
                for relax_s in self.relaxed_subject:
                    for relax_p in self.relaxed_predicat:
                        merged = NodeRelaxed.merge(relax_s, relax_p, dummy_obj)
                        self.add_node_relaxation(merged)
            else:
                if self.relaxed_object:
                    dummy_pred = NodeRelaxed(None, self.predicat_var, None, 1.0/3, [-2, 0, -2])
                    for relax_s in self.relaxed_subject:
                        for relax_o in self.relaxed_object:
                            merged = NodeRelaxed.merge(relax_s, dummy_pred, relax_o)
                            self.add_node_relaxation(merged)
                else:
                    dummy_pred = NodeRelaxed(None, self.predicat_var, None, 1.0/3, [-2, 0, -2])
                    dummy_obj = NodeRelaxed(None, None, self.object_var, 1.0/3, [-2, -2, 0])
                    for relax_s in self.relaxed_subject:
                        merged = NodeRelaxed.merge(relax_s, dummy_pred, dummy_obj)
                        self.add_node_relaxation(merged)
        else:
            # Si le sujet est une variable
            default_subject = NodeRelaxed(self.subject_var, None, None, 1.0/3, [0, -2, -2])
            if self.relaxed_predicat:
                if self.relaxed_object:
                    for relax_p in self.relaxed_predicat:
                        for relax_o in self.relaxed_object:
                            merged = NodeRelaxed.merge(default_subject, relax_p, relax_o)
                            self.add_node_relaxation(merged)
                else:
                    dummy_obj = NodeRelaxed(None, None, self.object_var, 1.0/3, [-2, -2, 0])
                    for relax_p in self.relaxed_predicat:
                        merged = NodeRelaxed.merge(default_subject, relax_p, dummy_obj)
                        self.add_node_relaxation(merged)
            else:
                default_pred = NodeRelaxed(None, self.predicat_var, None, 1.0/3, [-2, 0, -2])
                if self.relaxed_object:
                    for relax_o in self.relaxed_object:
                        merged = NodeRelaxed.merge(default_subject, default_pred, relax_o)
                        self.add_node_relaxation(merged)
                else:
                    raise ValueError("Unrelaxable triple")
        self.current_elt = -1

    def add_node_relaxation(self, node):
        """
        Ajoute un triplet relaxé (instance de NodeRelaxed) à la liste.
        Ici, nous nous contentons d'ajouter sans tri particulier.
        """
        self.relaxed_triple.append(node)

    def next_relaxed_triple(self):
        """
        Retourne le prochain triplet relaxé ou None s'il n'y en a plus.
        """
        self.current_elt += 1
        if self.current_elt >= len(self.relaxed_triple):
            return None
        return self.relaxed_triple[self.current_elt]

    def has_next(self):
        """
        Vérifie s'il reste des triplets relaxés à itérer.
        """
        return self.current_elt + 1 < len(self.relaxed_triple)

    def reset(self):
        """
        Réinitialise l'itérateur de relaxation.
        """
        self.current_elt = -1

# ---------------------------
# Exemple d'utilisation
# ---------------------------
if __name__ == "__main__":
   
    clause1=SimpleLiteral((URIRef("http://example.org/FullProfessor"), URIRef("http://example.org/teacherOf"), Literal("SW")))
    # 1️⃣ Initialisation du graphe RDF
    g = Graph()
    g.parse("graph.ttl", format="turtle")
    print("Triplet original:", clause1)
    # Instanciation de TripleRelaxation
    triple_relax = TripleRelaxation(clause1,g, order=SIM_ORDER)

    # Affichage des triplets relaxés générés
    print("Triples relaxés générés:")
    while triple_relax.has_next():
        relaxed = triple_relax.next_relaxed_triple()
        print(relaxed)
