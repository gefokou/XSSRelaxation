def expand_sparql(query):
    """
    Prend en entrée une requête SPARQL compacte (string) et retourne une chaîne
    où tous les préfixes sont développés en URIs complètes. Les triplets
    du WHERE sont formatés un par ligne. Les mots-clés SELECT, WHERE sont
    traités insensiblement à la casse.
    """

    import re

    # 1. Extraire les déclarations PREFIX et construire le dictionnaire prefixes
    prefix_pattern = re.compile(
        r'^\s*PREFIX\s+([A-Za-z][A-Za-z0-9_-]*)\s*:\s*<([^>]+)>',
        re.IGNORECASE | re.MULTILINE)
    prefixes = {}
    def collect_prefix(match):
        pré = match.group(1)   # nom du préfixe
        uri = match.group(2)   # URI correspondante
        prefixes[pré] = uri
        return ''  # on supprime la ligne PREFIX de la requête
    query_no_prefix = prefix_pattern.sub(collect_prefix, query)
    # Supprimer les lignes vides éventuelles issues de la suppression
    query_no_prefix = re.sub(r'(?m)^[ \t]*\n', '', query_no_prefix)

    # 2. Isoler la clause SELECT ... WHERE (insensible à la casse)
    select_match = re.search(r'(?i)SELECT\s+(.*?)\s+{', query_no_prefix, re.DOTALL)
    select_clause = select_match.group(1).strip() if select_match else ''
    # Mettre en majuscules DISTINCT/REDUCED s'ils sont présents
    parts = select_clause.split()
    if parts and parts[0].lower() in ('distinct', 'reduced'):
        parts[0] = parts[0].upper()
        select_clause = ' '.join(parts)

    # 3. Trouver la section WHERE { ... }
    where_match = re.search(r'(?i)\b\b', query_no_prefix)
    if not where_match:
        raise ValueError("Clause WHERE introuvable dans la requête.")
    brace_open = query_no_prefix.find('{', where_match.end())
    if brace_open == -1:
        raise ValueError("Accolade '{' après WHERE non trouvée.")
    # Correspondance des accolades pour trouver '}'
    level = 1
    i = brace_open + 1
    while i < len(query_no_prefix) and level > 0:
        if query_no_prefix[i] == '{':
            level += 1
        elif query_no_prefix[i] == '}':
            level -= 1
        i += 1
    if level != 0:
        raise ValueError("Accolades mal appariées dans la requête.")
    brace_close = i - 1
    where_content = query_no_prefix[brace_open+1:brace_close]

    # 4. Analyse du contenu entre { et } pour extraire les triplets
    triples = []
    subject = None
    predicate = None
    i = 0
    length = len(where_content)
    while i < length:
        ch = where_content[i]
        # Ignorer espaces
        if ch.isspace():
            i += 1
            continue
        # Gérer ';' : même sujet, reset du prédicat
        if ch == ';':
            predicate = None
            i += 1
            continue
        # Gérer ',' : même sujet et prédicat, nouvel objet
        if ch == ',':
            i += 1
            continue
        # Gérer '.' : fin d'un triplet
        if ch == '.':
            subject = None
            predicate = None
            i += 1
            continue

        # 4.1 Lecture d'un terme
        if ch == '<':
            # URI complète < ... >
            start = i
            i = where_content.find('>', i) + 1
            term = where_content[start:i]
        elif ch == '"' or ch == "'":
            # Littéral (éventuellement multiligne ou typé)
            quote = ch
            if where_content.startswith(quote*3, i):
                quote = quote*3  # triple quotes
            start = i
            i += len(quote)
            # Lire jusqu'à la fermeture du littéral
            while i < length:
                if where_content.startswith(quote, i):
                    i += len(quote)
                    break
                if where_content[i] == '\\':  # échappement
                    i += 2
                else:
                    i += 1
            term = where_content[start:i]
            # Vérifier un type ^^ ou un tag de langue @ après le littéral
            if where_content.startswith('^^', i):
                term += '^^'
                i += 2
                if where_content[i] == '<':
                    start = i
                    i = where_content.find('>', i) + 1
                    term += where_content[start:i]
                else:
                    # Préfixe:Type
                    m = re.match(r'([A-Za-z][A-Za-z0-9_-]*:[A-Za-z0-9_-]+)', where_content[i:])
                    if m:
                        term += m.group(1)
                        i += len(m.group(1))
            elif where_content.startswith('@', i):
                m = re.match(r'@[a-zA-Z\-]+', where_content[i:])
                if m:
                    term += m.group(0)
                    i += len(m.group(0))
        else:
            # Variable, blank node ou préfixe:Nom ou symbole 'a'
            if ch == '?':
                j = i+1
                while j < length and re.match(r'[A-Za-z0-9_]', where_content[j]):
                    j += 1
                term = where_content[i:j]
                i = j
            elif ch == '_':
                j = i+1
                while j < length and re.match(r'[A-Za-z0-9_]', where_content[j]):
                    j += 1
                term = where_content[i:j]
                i = j
            # elif ch == 'a':
            #     term = 'a'
            #     i += 1
            else:
                # Pour 'a' ou nom préfixé
                j = i
                while j < length and re.match(r'[:A-Za-z0-9_]', where_content[j]):
                    j += 1
                term = where_content[i:j]
                i = j

        # 4.2 Attribution du terme dans le triplet
        if subject is None:
            subject = term
        elif predicate is None:
            predicate = term
        else:
            obj = term
            triples.append((subject, predicate, obj))
            # Le sujet reste le même si un ';' suit, ou est remis à None si '.' déjà lu

    # 5. Fonction d'expansion d'un terme en URI complète si besoin
    def expand_term(t):
        # Variables, blank nodes, et 'a' restent inchangés
        if t.startswith('?') or t.startswith('_:') or t == 'a':
            return t
        # URI déjà complète
        if t.startswith('<') and t.endswith('>'):
            return t
        # Littéral avec éventuel type/lang
        if t.startswith('"') or t.startswith("'"):
            # Littéral typé
            if '^^' in t:
                lit, type_part = t.split('^^', 1)
                if not type_part.startswith('<'):
                    pré, local = type_part.split(':', 1)
                    if pré in prefixes:
                        type_part = '<' + prefixes[pré] + local + '>'
                return lit + '^^' + type_part
            # Littéral avec tag de langue
            if '@' in t:
                base, lang = t.rsplit('@', 1)
                return base + '@' + lang
            return t
        # Nom préfixé
        if ':' in t:
            pré, local = t.split(':', 1)
            if pré in prefixes:
                return '<' + prefixes[pré] + local + '>'
        # Nombre ou autre littéral sans modification
        return t

    # 6. Reconstruction de la requête développée
    output_lines = []
    output_lines.append("SELECT " + select_clause if select_clause else "SELECT")
    output_lines.append("WHERE {")
    for s, p, o in triples:
        s_exp = expand_term(s)
        if p == 'a':
            p_exp = '<http://www.w3.org/1999/02/22-rdf-syntax-ns#type>'
        else:
            p_exp = expand_term(p)
        o_exp = expand_term(o)
        output_lines.append(f"    {s_exp} {p_exp} {o_exp} .")
    output_lines.append("}")
    return "\n".join(output_lines)



# --- Exemple d'utilisation ---
if __name__ == "__main__":
    query1 = """
    PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX ex:   <http://example.org/>
    PREFIX xsd:  <http://www.w3.org/2001/XMLSchema#>

    SELECT ?p ?n
    {
      ?p rdf:type      ex:Lecturer;
         ex:nationality ?n;
         ex:teacherOf   "SW";
         ex:age         "46"^^xsd:integer .
    }
    """

    query2 = """ 
    prefix ub: <http://www.lehigh.edu/~zhp2/2004/0401/univ-bench.owl#>
    select ?x {
    ?x a ub:GraduateStudent;
        ub:takesCourse <http://www.Department0.University0.edu/GraduateCourse0>.
    }"""
    
    devquery1=expand_sparql(query1)
    devquery2=expand_sparql(query2)
    print("Requête SPARQL compacte 1:")
    print(query1)
    print("\nRequête SPARQL développée 1 \n:")
    print(devquery1)

    print("Requête SPARQL compacte 1:")
    print(query2)
    print("\nRequête SPARQL développée 1 :")
    print(devquery2)
        