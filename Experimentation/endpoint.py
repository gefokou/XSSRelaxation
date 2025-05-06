# endpoint.py
from rdflib import Graph
from rdflib_endpoint.sparql_endpoint import SparqlEndpoint
import uvicorn

# 1. Chargez le graphe RDF
D = Graph()
D.parse("Experimentation/Uni1.owl", format="xml")

# 2. Créez l'endpoint SPARQL
endpoint = SparqlEndpoint(
    graph=D,
    prefix="default",
    path="/sparql"
)

# 3. Ajoutez une route racine pour l'accueil
@endpoint.get("/")
def root():
    return {"message": "Bienvenue sur le SPARQL endpoint. Utilisez /sparql pour vos requêtes."}

# 4. Lancez le serveur Uvicorn
if __name__ == "__main__":
    uvicorn.run(endpoint,
                host="127.0.0.1",
                port=8000,
                log_level="info")
