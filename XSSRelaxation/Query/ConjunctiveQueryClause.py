from rdflib import Graph
from typing import List, Set, Optional
from rdflib.plugins.sparql.processor import SPARQLResult
from Query.SimpleLiteral import SimpleLiteral
from Query.FilterLiteral import FilterLiteral

class ConjunctiveQuery:
    def __init__(self):
        self.clauses: List[SimpleLiteral] = []
        self.filters: List[FilterLiteral] = []
        self.selected_vars: Set[str] = set()

    def add_clause(self, clause: SimpleLiteral):
        """Ajoute une clause SimpleLiteral (triplet) à la requête et met à jour les variables sélectionnées."""
        self.clauses.append(clause)
        # self.selected_vars.update(clause.mentioned_vars)

    # def add_filter(self, filter_clause: FilterLiteral):
    #     """Ajoute une clause FilterLiteral (filtre) à la requête et met à jour les variables sélectionnées."""
    #     self.filters.append(filter_clause)
    #     self.selected_vars.update(filter_clause.mentioned_vars)

    # def set_selected_variables(self, variables: set()):
    #     """Définit explicitement les variables à récupérer dans le SELECT."""
    #     self.selected_vars = variables

    @property
    def is_star_query(self) -> bool:
        """Retourne True si aucune variable spécifique n'est sélectionnée."""
        return len(self.selected_vars) == 0

    def to_sparql(self) -> str:
        """
        Génère la requête SPARQL complète avec :
         - Un retour à la ligne après chaque clause.
         - Le label de chaque clause affiché en commentaire (#) sur la même ligne.
        """
        select_clause = "SELECT *" if self.is_star_query else f"SELECT {' '.join(f'?{v}' for v in self.selected_vars)}"
        
        # Pour chaque clause simple, on ajoute le triple pattern suivi du label en commentaire sur la même ligne.
        where_clauses = [
            f"{clause.get_triple_pattern().strip()}  # {clause.label}" for clause in self.clauses
        ]
        # Pour chaque clause filtre, on affiche FILTER(expression) suivi du label en commentaire sur la même ligne.
        filter_clauses = [
            f"FILTER({flt.filter_expr})  # {flt.label}" for flt in self.filters
        ]
        where_body = "\n".join(where_clauses + filter_clauses)
        
        return f"{select_clause}\nWHERE {{\n{where_body}\n}}"

    def execute(self, graph: Graph) -> SPARQLResult:
        """Exécute la requête sur le graphe RDF passé en paramètre."""
        from rdflib.plugins.sparql import prepareQuery
        query = prepareQuery(self.to_sparql())
        return graph.query(query)

    def removepos(self, index: int):
        """
        Retire une clause par son index et la retourne
        Args:
            index: Position dans la liste combinée [triplets + filtres]
        Returns:
            La clause retirée (SimpleLiteral ou FilterLiteral)
        """
        total_simple = len(self.clauses)
        
        if index < 0 or index >= len(self.clauses):
            raise IndexError(f"Index {index} hors limites (max={len(self.clauses)-1})")
            
        # Cas d'un triplet simple
        if index < total_simple:
            return self.clauses.pop(index)
            
        # Cas d'un filtre
        filter_index = index - total_simple
        if filter_index < len(self.filters):
            return self.filters.pop(filter_index)
        
    def remove(self, element):
        """
        Supprime un élément spécifique de la requête.
        Si l'élément est présent plusieurs fois, seule la première occurrence est supprimée.
        
        :param element: L'élément à supprimer (ex: un triplet ou une sous-clause)
        :return: La requête après suppression de l'élément
        """
        if element in self.clauses:
            self.clauses.remove(element)
        return self  # Retourne l'objet mis à jour pour permettre le chaînage d'appels
    def remove_clause(self, clause): # type: ignore
        """
        Supprime une clause de la requête conjonctive.
        Args:
            clause: La clause à supprimer (SimpleLiteral ou FilterLiteral)
        """
        for i in clause.clauses:
            self.remove(i)
        
    def add(self, clause, index: int):
        """
        Ajoute une clause à une position spécifique 
        (Complément de remove_clause pour les opérations de réinsertion)
        """
        if isinstance(clause, SimpleLiteral):
            self.clauses.insert(index, clause)
        elif isinstance(clause, FilterLiteral):
            # Ajuste l'index pour les filtres
            adj_index = index - len(self.clauses)
            self.filters.insert(adj_index, clause)
        else:
            raise TypeError("Type de clause non supporté")
        
        # Mise à jour des variables sélectionnées
        self.selected_vars.update(clause.selected_vars)

    def clone(self):
        """
        Crée une copie profonde de la requête conjonctive
        Returns:
            Une nouvelle instance de ConjunctiveQuery identique
        """
        # Création d'une nouvelle instance
        clone = ConjunctiveQuery()
        
        # Copie des triplets simples
        # Chaque clause dans self.clauses est un SimpleLiteral, donc on accède à son triplet
        clone.clauses = [clause for clause in self.clauses]
        
        # # Copie des filtres
        # clone.filters = [FilterLiteral(fl.filter_expr) for fl in self.filters]
        
        # Copie des variables sélectionnées
        clone.selected_vars = self.selected_vars.copy()
        
        return clone
    def is_valid(self) -> bool:
        return len(self.clauses) > 0
    def is_subquery(self, other: 'ConjunctiveQuery') -> bool:
        """Vérifie si cette requête est incluse dans une autre"""
        # Vérification des triplets
        for sl in self.clauses:
            if not any(sl.triple == other_sl.triple for other_sl in other.clauses):
                return False
        
        # Vérification des filtres
        # for fl in self.filters:
        #     if not any(fl.filter_expr == other_fl.filter_expr for other_fl in other.filters):
        #         return False
                
        return True
    
    @staticmethod
    def conjunction_query_union(query: 'ConjunctiveQuery',
                                core: 'ConjunctiveQuery') -> 'ConjunctiveQuery':
        """
        Retourne une nouvelle instance de ConjunctiveQueryClause qui est l'union
        des clauses de 'query' et de 'core'. Les clauses déjà présentes dans 'core'
        ne sont pas dupliquées.

        :param query: La requête source dont on souhaite extraire des clauses.
        :param core: L'accumulateur de clauses.
        :return: Une nouvelle instance contenant toutes les clauses de 'core' et
                 celles de 'query' qui ne sont pas déjà présentes.
        """
        # On clone 'core' pour éviter de le modifier directement.
        new_query = core.clone()
        # Pour chaque clause présente dans 'query', on l'ajoute à new_query si elle n'y figure pas déjà.
        for clause in query.clauses:
            if clause not in new_query.clauses:
                new_query.add_clause(clause)
        # new_query.selected_vars = query.selected_vars.copy()
        return new_query

    def __repr__(self) -> str:
        return f"<ConjunctiveQuery | Clauses: {len(self.clauses)}, Filters: {len(self.filters)}, Vars: {self.selected_vars}>"
