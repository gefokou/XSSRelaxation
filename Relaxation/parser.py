import re
from typing import Optional, Union
from rdflib import URIRef, Literal, Variable, BNode
from Query.ConjunctiveQueryClause import ConjunctiveQuery
from Query.SimpleLiteral import SimpleLiteral
from Query.FilterLiteral import FilterLiteral

class SPARQLToConjunctiveQuery:
    """
    Parseur amélioré avec support complet des littéraux typés SPARQL
    """
    @staticmethod
    def parse(sparql: str) -> ConjunctiveQuery:
        lines = sparql.strip().splitlines()
        cq = ConjunctiveQuery()
        in_where = False
        
        for raw in lines:
            line = raw.strip()
            
            # Gestion du SELECT
            if not in_where and line.upper().startswith("SELECT"):
                SPARQLToConjunctiveQuery._parse_select(line, cq)
                continue
                
            # Début du WHERE
            if "WHERE" in line and "{" in line:
                in_where = True
                continue
                
            # Fin du WHERE
            if in_where and "}" in line:
                break
                
            # Contenu du WHERE
            if not in_where or not line or line.startswith("#"):
                continue
                
            # Séparation pattern/commentaire
            pattern, *comment = line.split('#', 1)
            pattern = pattern.strip()
            label = comment[0].strip() if comment else ''
            
            # Filtres
            if pattern.upper().startswith("FILTER"):
                SPARQLToConjunctiveQuery._parse_filter(pattern, label, cq)
                continue
                
            # Triplets
            if '.' in pattern:
                pattern = pattern.rstrip('.').strip()
                
            if pattern:
                SPARQLToConjunctiveQuery._parse_triple_pattern(pattern, label, cq)

        return cq

    @staticmethod
    def _parse_select(line: str, cq: ConjunctiveQuery):
        vars_ = re.findall(r"\?([A-Za-z0-9_]+)", line)
        if vars_ and vars_[0] != '*':
            cq.set_selected_variables(vars_)

    @staticmethod
    def _parse_filter(pattern: str, label: str, cq: ConjunctiveQuery):
        m = re.match(r"FILTER\s*\((.*)\)", pattern, re.IGNORECASE)
        if m:
            fl = FilterLiteral(m.group(1).strip())
            fl.label = label
            cq.add_filter(fl)

    @staticmethod
    def _parse_triple_pattern(pattern: str, label: str, cq: ConjunctiveQuery):
        tokens = re.split(r'\s+', pattern, 2)
        if len(tokens) != 3:
            return

        s, p, o = tokens
        nodes = [
            SPARQLToConjunctiveQuery._parse_node(s),
            SPARQLToConjunctiveQuery._parse_node(p),
            SPARQLToConjunctiveQuery._parse_node(o)
        ]
        
        if all(nodes):
            sl = SimpleLiteral((nodes[0], nodes[1], nodes[2]))
            sl.label = label
            cq.add_clause(sl)

    @staticmethod
    def _parse_node(tok: str) -> Optional[Union[URIRef, Literal, BNode]]:
        # Variable
        if tok.startswith('?'):
            return Variable(tok[1:])
            
        # URIRef
        if tok.startswith('<') and tok.endswith('>'):
            return URIRef(tok[1:-1])
            
        # Littéral typé avec datatype
        typed_lit = re.match(r'^"(.+)"\^\^<(.+)>$', tok)
        if typed_lit:
            value, dtype = typed_lit.groups()
            return Literal(value, datatype=URIRef(dtype))
            
        # Littéral avec langue
        lang_lit = re.match(r'^"(.+)"@([a-z]+(-[a-z0-9]+)*)$', tok)
        if lang_lit:
            value, lang, _ = lang_lit.groups()
            return Literal(value, lang=lang)
            
        # Littéral simple
        if tok.startswith('"'):
            end_quote = tok.rfind('"')
            if end_quote > 0:
                return Literal(tok[1:end_quote])
            return Literal(tok[1:])
            
        # Blank node
        if tok.startswith('_:'):
            return BNode(tok[2:])
            
        # Littéral numérique/non-échappé
        if tok.replace('.', '', 1).isdigit():  # Gestion basique des nombres
            return Literal(tok)
            
        # Par défaut considère comme URIRef
        return URIRef(tok)

if __name__ == "__main__":
    # Exemple d'utilisation
    query='''SELECT ?p ?n
WHERE {
?p <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://example.org/Lecturer> .  # t0
?p <http://example.org/nationality> ?n .  # t1
?p <http://example.org/teacherOf> "SW" .  # t2
?p <http://example.org/age> "46"^^<http://www.w3.org/2001/XMLSchema#integer> .  # t3
}'''
    cq = SPARQLToConjunctiveQuery().parse(query)
    print(cq.to_sparql())
    # Affiche la requête conjonctive résultante
    print("Requête conjonctive :")
    print(cq.to_sparql())
    print("Variables sélectionnées :")
    print(cq.selected_vars)
    print("Clauses :")
    for clause in cq.clauses:
        print(clause.label)