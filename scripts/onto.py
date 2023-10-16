import hashlib
import json
import shutil

import kuzu
import numpy as np
import pandas as pd


def convert_to_hex(text):
    return "".join(hex(ord(c)) for c in text).encode()


def node_hash(node):
    return hashlib.md5(json.dumps(node).encode("utf-8")).hexdigest()


def build_table(conn):
    # create node tables
    conn.execute(
        "CREATE NODE TABLE OntoSource(name STRING, version STRING, node_id STRING, PRIMARY KEY (node_id))"
    )
    conn.execute(
        """
        CREATE NODE TABLE OntoTerm(id STRING, name STRING, definition STRING, 
        namespace STRING[], deprecated BOOLEAN, synonyms STRING[], 
        synonyms_xrefs STRING[], synonyms_str STRING, xrefs STRING[], alternative_ids STRING[], 
        version STRING, source STRING, node_id STRING,
        PRIMARY KEY (node_id))
    """
    )
    conn.execute("CREATE REL TABLE source(FROM OntoTerm TO OntoSource, version STRING)")
    conn.execute("CREATE REL TABLE child(FROM OntoTerm TO OntoTerm, version STRING)")
    conn.execute("CREATE REL TABLE parent(FROM OntoTerm TO OntoTerm, version STRING)")


def parse_ontology(file, source, version):
    onto = json.load(open(file, "r"))

    sources = []
    nodes = []
    source_rels = []
    child_rels = []
    parent_rels = []

    src_hashed = node_hash(f"{source}_{version}")
    sources.append(
        {"name": f"{source}", "version": f"{version}", "node_id": src_hashed}
    )
    all_node_ids = []

    for graph in onto["graphs"]:
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

                all_node_ids.append(f"{r['id']}")

                node_hashed = node_hash(f"{source}_{version}_{r['id']}")

                nodes.append(
                    {
                        "id": f"{r['id']}",
                        "name": f"{r['name']}",
                        "definition": json.loads(json.dumps(r["definition"])).replace(
                            '"', ""
                        ),
                        "namespace": list(np.unique(r["namespace"])),
                        "deprecated": f"{r['deprecated']}",
                        "synonyms": list(np.unique(r["synonyms"])),
                        "synonyms_xrefs": list(np.unique(r["synonyms_xrefs"])),
                        "synonyms_str": "",  # convert_to_hex(",".join(r['synonyms'])),
                        "xrefs": list(np.unique(r["xrefs"])),
                        "alternative_ids": list(np.unique(r["alternative_ids"])),
                        "version": f"{version}",
                        "source": f"{source}",
                        "node_id": node_hashed,
                    }
                )

                source_rels.append(
                    {
                        "from": node_hashed,
                        "to": src_hashed,
                        "version": f"{source}_{version}",
                    }
                )

        all_node_idx = pd.Index(all_node_ids)

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

            if (
                "#" in n_from
                or "#" in n_to
                or (n_from not in all_node_idx)
                or (n_to not in all_node_idx)
            ):
                continue

            from_hashed = node_hash(f"{source}_{version}_{n_from}")
            to_hashed = node_hash(f"{source}_{version}_{n_to}")

            child_rels.append(
                {"from": from_hashed, "to": to_hashed, "version": f"{source}_{version}"}
            )
            parent_rels.append(
                {"from": to_hashed, "to": from_hashed, "version": f"{source}_{version}"}
            )

    return sources, nodes, source_rels, parent_rels, child_rels


ontologies = [
    (
        "./kokoro/scripts/ontologies/EFO/v3.39.1.json",
        "Experimental Factor Ontology",
        "v3.39.1",
    ),
    # ("./kokoro/scripts/ontologies/UBERON/v2021-02-12.json", "UBERON", "v2021-02-12"),
    ("./kokoro/scripts/ontologies/UBERON/v2022-02-21.json", "UBERON", "v2022-02-21"),
    # ("./kokoro/scripts/ontologies/CL/v2021-06-21.json", "Cell Ontology", "v2021-06-21"),
    # ("./kokoro/scripts/ontologies/CL/v2022-02-16.json", "Cell Ontology", "v2022-02-16"),
    # ("./kokoro/scripts/ontologies/DOID/v2021--6-08.json", "Human Disease Ontology", "v2021--6-08"),
    (
        "./kokoro/scripts/ontologies/DOID/v2022-03-02.json",
        "Human Disease Ontology",
        "v2022-03-02",
    ),
    (
        "./kokoro/scripts/ontologies/MONDO/v2022-03-01.json",
        "Mondo Disease Ontology",
        "v2022-03-01",
    ),
    ("./kokoro/scripts/ontologies/CL/v2023-04-20.json", "Cell Ontology", "v2023-04-20"),
]

sources = []
nodes = []
source_rels = []
child_rels = []
parent_rels = []

for ontfile in ontologies:
    res = parse_ontology(*ontfile)
    sources.extend(res[0])
    nodes.extend(res[1])
    source_rels.extend(res[2])
    child_rels.extend(res[3])
    parent_rels.extend(res[4])


pd.DataFrame.from_records(sources, index=None).to_csv(
    "sources.csv", header=False, index=False
)
pd.DataFrame.from_records(nodes, index=None).drop_duplicates("node_id").to_csv(
    "nodes.csv", header=False, index=False
)
pd.DataFrame.from_records(source_rels, index=None).to_csv(
    "source_rels.csv", header=False, index=False
)
pd.DataFrame.from_records(parent_rels, index=None).to_csv(
    "parent_rels.csv", header=False, index=False
)
pd.DataFrame.from_records(child_rels, index=None).to_csv(
    "child_rels.csv", header=False, index=False
)

db_name = "onto_schub"

shutil.rmtree(f"./{db_name}", ignore_errors=True)

db = kuzu.Database(f"./{db_name}", buffer_pool_size=1024**3)
conn = kuzu.Connection(db)

build_table(conn)

conn.execute('COPY OntoSource FROM "sources.csv";')
conn.execute('COPY OntoTerm FROM "nodes.csv";')
conn.execute('COPY source FROM "source_rels.csv";')
conn.execute('COPY child FROM "child_rels.csv";')
conn.execute('COPY parent FROM "parent_rels.csv";')
