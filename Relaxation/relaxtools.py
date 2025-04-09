import itertools
import rdflib
from rdflib import Graph, URIRef, Literal, Variable
from Query.ConjunctiveQueryClause import ConjunctiveQuery
from Query.SimpleLiteral import SimpleLiteral
from rdflib import RDFS

# ---------------------------
# Constants and Global Counters
# ---------------------------
SUPPRESS_NODE_LEVEL = -1    # Relaxation level for node suppression
LEVEL_ORDER = 0             # Relaxation order by level
SIM_ORDER = 1               # Relaxation order by similarity
HYBRID_ORDER = 2            # Hybrid relaxation order

num_resource_release = 0    # Counter for resource variables
num_pred_release = 0        # Counter for predicate variables

# ---------------------------
# Similarity and Superclass/Property Functions
# ---------------------------
def similarity_measure_class(original_node, relaxed_node):
    """
    Calculate similarity between two nodes (subject or object).
    - Same node: 1.0
    - Relaxed to variable: 0.9
    - Default: 0.9 (simplified for demonstration)
    """
    if original_node == relaxed_node:
        return 1.0
    elif isinstance(relaxed_node, Variable):
        return 0.9
    return 0.9  # Default for superclass or other relaxations

def similarity_measure_property(original_node, relaxed_node):
    """
    Calculate similarity for predicates.
    - Same node: 1.0
    - Relaxed to variable: 0.9
    - Default: 0.9 (simplified for demonstration)
    """
    if original_node == relaxed_node:
        return 1.0
    elif isinstance(relaxed_node, Variable):
        return 0.9
    return 0.9  # Default for superproperty or other relaxations

def get_super_classes(uri, graph):
    """
    Retrieve superclasses for a URIRef from the graph.
    Returns a dict {superclass: relaxation_level}.
    """
    if not isinstance(uri, URIRef):
        return {}
    super_classes = {}
    for _, _, super_class in graph.triples((uri, RDFS.subClassOf, None)):
        super_classes[super_class] = 1
    if not super_classes:
        default_super = URIRef(str(uri).replace("P", "SuperP"))
        super_classes[default_super] = 1
    return super_classes

def get_super_properties(uri, graph):
    """
    Retrieve superproperties for a URIRef from the graph.
    Returns a dict {superproperty: relaxation_level}.
    """
    if not isinstance(uri, URIRef):
        return {}
    super_properties = {}
    for _, _, super_property in graph.triples((uri, RDFS.subPropertyOf, None)):
        super_properties[super_property] = 1
    if not super_properties:
        default_super = URIRef(str(uri).replace("P", "SuperP"))
        super_properties[default_super] = 1
    return super_properties

# ---------------------------
# Relaxed Node Class
# ---------------------------
class NodeRelaxed:
    def __init__(self, node_1, node_2, node_3, similarity, relaxation_levels):
        """
        node_1: subject
        node_2: predicate
        node_3: object
        similarity: similarity score (float)
        relaxation_levels: list of integers for each component's relaxation level
        """
        self.node_1 = node_1
        self.node_2 = node_2
        self.node_3 = node_3
        self.query=ConjunctiveQuery()
        self.query.add_clause(SimpleLiteral((self.node_1,self.node_2,self.node_3)))
        self.similarity = similarity
        self.relaxation_levels = relaxation_levels

    @staticmethod
    def merge(relax_s, relax_p, relax_o):
        """
        Merge relaxations for subject, predicate, and object into a single relaxed triple.
        """
        sim = (relax_s.similarity + relax_p.similarity + relax_o.similarity) / 3.0
        levels = [relax_s.relaxation_levels[0], relax_p.relaxation_levels[1], relax_o.relaxation_levels[2]]
        return NodeRelaxed(relax_s.node_1, relax_p.node_2, relax_o.node_3, sim, levels)

    def get_relaxation_level(self):
        """Return the total relaxation level (sum of individual levels)."""
        return sum(self.relaxation_levels)

    def __repr__(self):
        return f"{self.query}                        sim={self.similarity})"

# ---------------------------
# Triple Relaxation Class
# ---------------------------
class TripleRelaxation:
    def __init__(self, clause, graph, order=SIM_ORDER):
        """
        clause: RDF triple as a tuple (subject, predicate, object) using rdflib.
        graph: RDF graph (rdflib.Graph).
        order: Relaxation order (SIM_ORDER by default).
        """
        global num_resource_release, num_pred_release
        self.graph = graph  # Changed from session to graph for clarity
        self.current_clause = clause
        self.relaxation_order = order
        self.subject_var = None
        self.object_var = None
        self.predicat_var = None
        self.relaxed_subject = []
        self.relaxed_predicat = []
        self.relaxed_object = []
        self.relaxed_triple = []
        self.current_elt = -1

        self.triple_relaxation(clause)

    def relax_node(self, original_node):
        """
        Relax a node (subject or object), handling both URIRef and Literal.
        Returns a dict {alternative_node: relaxation_level}.
        """
        global num_resource_release
        relaxed_node = {}
        if isinstance(original_node, URIRef):
            relaxed_node[original_node] = 0  # Keep original
            relaxed_node.update(get_super_classes(original_node, self.graph))  # Add superclasses
            var_name = f"R{num_resource_release}"
            num_resource_release += 1
            var_node = Variable(var_name)
            relaxed_node[var_node] = SUPPRESS_NODE_LEVEL  # Replace with variable
        elif isinstance(original_node, Literal):
            relaxed_node[original_node] = 0  # Keep original
            var_name = f"R{num_resource_release}"
            num_resource_release += 1
            var_node = Variable(var_name)
            relaxed_node[var_node] = SUPPRESS_NODE_LEVEL  # Replace with variable
        else:  # Already a variable
            relaxed_node[original_node] = 0
        return relaxed_node

    def relax_predicate(self, original_node):
        """
        Relax a predicate, handling both URIRef and Literal.
        Returns a dict {alternative_node: relaxation_level}.
        """
        global num_pred_release
        relaxed_node = {}
        if isinstance(original_node, URIRef):
            relaxed_node[original_node] = 0  # Keep original
            relaxed_node.update(get_super_properties(original_node, self.graph))  # Add superproperties
            var_name = f"P{num_pred_release}"
            num_pred_release += 1
            var_node = Variable(var_name)
            relaxed_node[var_node] = SUPPRESS_NODE_LEVEL  # Replace with variable
        elif isinstance(original_node, Literal):
            relaxed_node[original_node] = 0  # Keep original
            var_name = f"P{num_pred_release}"
            num_pred_release += 1
            var_node = Variable(var_name)
            relaxed_node[var_node] = SUPPRESS_NODE_LEVEL  # Replace with variable
        else:  # Already a variable
            relaxed_node[original_node] = 0
        return relaxed_node

    def triple_relaxation(self, clause):
        """
        Apply relaxation to the triple (clause).
        """
        subject, predicate, obj = clause.triple

        # Relax subject
        self.relaxed_subject = []
        subj_relax = self.relax_node(subject)
        for node, level in subj_relax.items():
            sim = similarity_measure_class(subject, node) / 3.0
            self.relaxed_subject.append(NodeRelaxed(node, None, None, sim, [level, -2, -2]))

        # Relax object
        self.relaxed_object = []
        obj_relax = self.relax_node(obj)
        for node, level in obj_relax.items():
            sim = similarity_measure_class(obj, node) / 3.0
            self.relaxed_object.append(NodeRelaxed(None, None, node, sim, [-2, -2, level]))

        # Relax predicate
        self.relaxed_predicat = []
        pred_relax = self.relax_predicate(predicate)
        for node, level in pred_relax.items():
            sim = similarity_measure_property(predicate, node) / 3.0
            self.relaxed_predicat.append(NodeRelaxed(None, node, None, sim, [-2, level, -2]))

        # Generate all relaxed triples
        self.all_triple_relaxation()

    def all_triple_relaxation(self):
        """
        Generate all possible relaxed triple combinations.
        """
        self.relaxed_triple = []
        for relax_s in self.relaxed_subject:
            for relax_p in self.relaxed_predicat:
                for relax_o in self.relaxed_object:
                    merged = NodeRelaxed.merge(relax_s, relax_p, relax_o)
                    self.add_node_relaxation(merged)
        self.current_elt = -1

    def add_node_relaxation(self, node):
        """Add a relaxed triple to the list."""
        self.relaxed_triple.append(node)

    def next_relaxed_triple(self):
        """Return the next relaxed triple or None if none remain."""
        self.current_elt += 1
        if self.current_elt >= len(self.relaxed_triple):
            return None
        return self.relaxed_triple[self.current_elt]

    def has_next(self):
        """Check if more relaxed triples are available."""
        return self.current_elt + 1 < len(self.relaxed_triple)

    def reset(self):
        """Reset the relaxation iterator."""
        self.current_elt = -1

class ConjunctiveQueryRelaxation:
    def __init__(self, query: ConjunctiveQuery, graph: Graph, order=SIM_ORDER):
        """
        Initialise la relaxation d'une requête conjonctive.
        
        Args:
            query (ConjunctiveQuery): La requête initiale contenant plusieurs clauses.
            graph (Graph): La base de données RDF (un rdflib.Graph).
            order (int): L'ordre de relaxation (par défaut SIM_ORDER).
        """
        self.query = query
        self.graph = graph
        self.order = order

    def relax_query(self) -> list:
        """
        Génère des versions relaxées de la requête conjonctive en relaxant chacune de ses clauses.
        
        Returns:
            list: Liste des requêtes (ConjunctiveQuery) relaxées.
        """
        # Pour chaque clause de la requête, on récupère la liste des clauses relaxées
        relaxed_versions_per_clause = []
        
        for clause in self.query.clauses:
            # On crée une instance de TripleRelaxation pour la clause
            triple_relax = TripleRelaxation(clause, self.graph, order=self.order)
            # Liste des versions relaxées pour cette clause
            relaxed_clause_list = []
            while triple_relax.has_next():
                relaxed_triple = triple_relax.next_relaxed_triple()
                # On suppose que relaxed_triple.query.clauses[0] contient la clause relaxée
                relaxed_clause = relaxed_triple.query.clauses[0]
                relaxed_clause_list.append(relaxed_clause)
            # Si aucune version relaxée n'a été générée pour une clause, on garde la clause originale
            if not relaxed_clause_list:
                relaxed_clause_list.append(clause)
            relaxed_versions_per_clause.append(relaxed_clause_list)
        
        # Combiner les relaxations de toutes les clauses par produit cartésien
        all_relaxed_queries = []
        for combination in itertools.product(*relaxed_versions_per_clause):
            new_query = ConjunctiveQuery()
            for clause in combination:
                new_query.add_clause(clause)
            all_relaxed_queries.append(new_query)
        
        return all_relaxed_queries

# --- Exemple d'utilisation ---
if __name__ == "__main__":
    # Création d'une instance de ConjunctiveQuery avec plusieurs clauses.
    cq = ConjunctiveQuery()
    # On ajoute deux clauses, par exemple.
    clause1 = SimpleLiteral((URIRef("http://example.org/FullProfessor"),
                             URIRef("http://example.org/teacherOf"),
                             Literal("SW")))
    clause2 = SimpleLiteral((URIRef("http://example.org/s2"),
                             URIRef("http://example.org/nationality"),
                             Literal("US")))
    cq.add_clause(clause1)
    cq.add_clause(clause2)
    
    # Création d'une base de données RDF (peut être initialisée depuis un fichier ou construite dynamiquement)
    g = Graph()
    # Par exemple, pour charger un fichier Turtle, décommentez la ligne suivante :
    g.parse("graph.ttl", format="turtle")
    
    # Instanciation du processus de relaxation pour la requête conjonctive
    cqr = ConjunctiveQueryRelaxation(cq, g, order=SIM_ORDER)
    relaxed_queries = cqr.relax_query()
    relaxed_queries.pop(0)  # Suppression de la première requête (originale)
    # Affichage des requêtes relaxées générées
    print("Nombre de requêtes relaxées générées:", len(relaxed_queries))
    for rq in relaxed_queries:
        print(f"{[i for i in rq.clauses]}")
# ---------------------------
# Example Usage
# ---------------------------
# if __name__ == "__main__":
#     # Initialize RDF graph
#     g = Graph()
#     # g.parse("graph.ttl", format="turtle")  # Uncomment and provide a file if needed

#     # Define a triple with a Literal
#     clause1 = SimpleLiteral((URIRef("http://example.org/FullProfessor"), 
#                              URIRef("http://example.org/teacherOf"), 
#                              Literal("SW")))
#     print("Triplet original:", clause1)

#     # Instantiate TripleRelaxation
#     triple_relax = TripleRelaxation(clause1, g, order=SIM_ORDER)

#     # Display generated relaxed triples
#     print("Triples relaxés générés:")
#     while triple_relax.has_next():
#         relaxed = triple_relax.next_relaxed_triple()
#         print(relaxed)