import json
import os

import numpy as np
from gdb import graphManager

BATCH_SIZE = 500


def batch_write(gdb, queries):
    gdb.batch_add_to_graph(queries)


def parse_ontology(file, source, version):
    gdb = graphManager(
        f"bolt://{os.getenv('NEO4J_SERVER')}:7687",
        os.getenv("NEO4J_USER"),
        os.getenv("NEO4J_PASS"),
    )

    # create indexes
    gdb.add_to_graph(
        """
            CREATE INDEX ds_id IF NOT EXISTS FOR (d:Dataset) ON (d.id)
        """
    )

    gdb.add_to_graph(
        """
            CREATE INDEX expt_id IF NOT EXISTS FOR (e:Experiment) ON (e.id)
        """
    )

    gdb.add_to_graph(
        """
            CREATE INDEX e_search IF NOT EXISTS FOR (e:Experiment) ON (e.keyword, e.description, e.title)
        """
    )

    gdb.add_to_graph(
        """
            CREATE INDEX onto_id IF NOT EXISTS FOR (o:OntoTerm) ON (o.id)
        """
    )

    gdb.add_to_graph(
        """
            CREATE INDEX onto_all IF NOT EXISTS FOR (o:OntoTerm) ON (o.source, o.version, o.name)
        """
    )

    onto = json.load(open(file, "r"))

    gdb.add_to_graph(
        f"""
            MERGE (o:OntoSource {{ source: \"{source}\", version: \"{version}\"}})
        """
    )

    queries = []

    for graph in onto["graphs"]:
        print(graph.keys())

        for node in graph["nodes"]:
            if "type" in node and node["type"].lower() == "class":
                r = {
                    "id": node["id"].split("/")[-1].replace("_", ":")
                    if "/" in node["id"]
                    else node["id"].replace("_", ":"),
                    "name": node["lbl"] if "lbl" in node else "",
                    "definition": "",
                    "namespace": [],
                    "deprecated": False,
                    "synonyms": [],
                    "synonyms_xrefs": [],
                    "xrefs": [],
                    "alternative_ids": [],
                }

                if "meta" in node:
                    # get namespace/ term entity type
                    if "basicPropertyValues" in node["meta"]:
                        for bprop in node["meta"]["basicPropertyValues"]:
                            if (
                                bprop["pred"].endswith("OBONamespace")
                                and "val" in bprop
                            ):
                                r["namespace"].append(bprop["val"])

                            if (
                                bprop["pred"].endswith("hasAlternativeId")
                                and "val" in bprop
                            ):
                                r["alternative_ids"].append(bprop["val"])

                            if bprop["pred"].endswith("consider") and "val" in bprop:
                                r["alternative_ids"].append(bprop["val"])

                    if "definition" in node["meta"]:
                        r["definition"] = (
                            node["meta"]["definition"]["val"]
                            if "val" in node["meta"]["definition"]
                            else ""
                        )

                    if "deprecated" in node["meta"]:
                        r["deprecated"] = node["meta"]["deprecated"]

                    if "synonyms" in node["meta"]:
                        for syn in node["meta"]["synonyms"]:
                            if "val" in syn:
                                r["synonyms"].append(syn["val"])

                            if "xrefs" in syn and len(syn["xrefs"]) > 0:
                                r["synonyms_xrefs"].extend(syn["xrefs"])

                    if "xrefs" in node["meta"]:
                        for xref in node["meta"]["xrefs"]:
                            if "val" in xref:
                                r["xrefs"].append(xref["val"])

                queries.append(
                    f"""
                        MATCH (os:OntoSource {{ source: \"{source}\", version: \"{version}\"}})
                        MERGE (ot:OntoTerm {{ id: \"{r['id']}\", name: {json.dumps(r['name'])}, 
                        namespace: {list(np.unique(r['namespace']))}, deprecated: \"{r['deprecated']}\", 
                        synonyms: {list(np.unique(r['synonyms']))}, 
                        synonyms_xrefs: {list(np.unique(r['synonyms_xrefs']))},
                        synonyms_str: {json.dumps(",".join(r['synonyms']))},
                        xrefs: {list(np.unique(r['xrefs']))}, definition: {json.dumps(r['definition'])},
                        version: \"{version}\",
                        source: \"{source}\",
                        alternative_ids: {list(np.unique(r['alternative_ids']))}
                        }})
                        with os, ot 
                        CREATE (ot)-[:source {{ version: \"{version}\" }}]->(os) 
                    """
                )

                for ns in np.unique(r["namespace"]):
                    queries.append(
                        f"""
                        MATCH (ot:OntoTerm {{ id: \"{r['id']}\", version: \"{version}\"}})
                        MERGE (ont:OntoNamespace {{ name: \"{ns}\" }})
                        with ot, ont 
                        CREATE (ot)-[:namespace {{ version: \"{version}\" }}]->(ont) 
                    """
                    )

            if len(queries) >= BATCH_SIZE:
                batch_write(gdb, queries)
                queries = []

        batch_write(gdb, queries)
        queries = []

        for edge in graph["edges"]:
            n_from = (
                edge["obj"].split("/")[-1].replace("_", ":")
                if "/" in edge["obj"]
                else edge["obj"].replace("_", ":")
            )
            n_to = (
                edge["sub"].split("/")[-1].replace("_", ":")
                if "/" in edge["sub"]
                else edge["sub"].replace("_", ":")
            )

            queries.append(
                f"""
                    MATCH (ofrom:OntoTerm {{ id: \"{n_from}\", version: \"{version}\"}})
                    MATCH (oto:OntoTerm {{ id: \"{n_to}\", version: \"{version}\"}})
                    with ofrom, oto
                    MERGE (ofrom)-[:child {{ source: \"{source}\", version: \"{version}\" }}]->(oto) 
                    MERGE (ofrom)<-[:parent {{ source: \"{source}\", version: \"{version}\" }}]-(oto) 
                """
            )

            if len(queries) >= BATCH_SIZE:
                batch_write(gdb, queries)
                queries = []

        batch_write(gdb, queries)
        queries = []


parse_ontology(
    "./ontologies/EFO/v3.39.1.json", "Experimental Factor Ontology", "v3.39.1"
)

# parse_ontology("./ontologies/UBERON/v2021-02-12.json", "UBERON", "v2021-02-12")
parse_ontology("./ontologies/UBERON/v2022-02-21.json", "UBERON", "v2022-02-21")

# parse_ontology("./ontologies/CL/v2021-06-21.json", "Cell Ontology", "v2021-06-21")
# parse_ontology("./ontologies/CL/v2022-02-16.json", "Cell Ontology", "v2022-02-16")

# parse_ontology(
#     "./ontologies/DOID/v2021--6-08.json", "Human Disease Ontology", "v2021--6-08"
# )
parse_ontology(
    "./ontologies/DOID/v2022-03-02.json", "Human Disease Ontology", "v2022-03-02"
)

parse_ontology(
    "./ontologies/MONDO/v2022-03-01.json", "Mondo Disease Ontology", "v2022-03-01"
)

parse_ontology("./ontologies/CL/v2023-04-20.json", "Cell Ontology", "v2023-04-20")
