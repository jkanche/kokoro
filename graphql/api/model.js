const { gql } = require("apollo-server");

const typeDefs = gql`
  type OntoTerm {
    name: String
    id: String
    alternative_ids: [String]
    alternative_ids_nodes: [OntoTerm] @cypher(
        statement: """
            MATCH (d:OntoTerm)
            where d.id IN this.alternative_ids
            RETURN d;
        """
      )
    definition: String
    deprecated: Boolean
    synonyms: [String]
    synonyms_str: String
    synonyms_xrefs: [String]
    synonyms_xrefs_nodes: [OntoTerm] @cypher(
        statement: """
            MATCH (d:OntoTerm)
            where d.id IN this.synonyms_xrefs
            RETURN d;
        """
      )
    version: String
    source: String
    xrefs: [String]
    xrefs_nodes: [OntoTerm] @cypher(
        statement: """
            MATCH (d:OntoTerm)
            where d.id IN this.xrefs
            RETURN d;
        """
      )
    child: [OntoTerm] @relationship(type: "child", direction: OUT)
    parent: [OntoTerm] @relationship(type: "parent", direction: OUT)
    namespace: [OntoNamespace] @relationship(type: "namespace", direction: OUT)
    experiments: [Experiment] @relationship(type: "links", direction: OUT)
    ancestors(limit: Int = 10, offset: Int = 0): [OntoTerm] @cypher(
        statement: """
            MATCH (this)
            CALL apoc.path.subgraphNodes(o, {
                    relationshipFilter: 'parent>',
                    labelFilter: '>OntoTerm'
                })
            YIELD node
            RETURN distinct node SKIP $offset LIMIT $limit;
        """
      )
    descendants(limit: Int = 10, offset: Int = 0): [OntoTerm] @cypher(
        statement: """
            MATCH (this)
            CALL apoc.path.subgraphNodes(o, {
                    relationshipFilter: 'child>',
                    labelFilter: '>OntoTerm'
                })
            YIELD node
            RETURN distinct node SKIP $offset LIMIT $limit;
        """
      )
  }

  type OntoSource {
    source: String
    version: String
  }

  type Source {
    id: String
  }

  type OntoNamespace {
    name: String
  }

  type Experiment {
    id: String
    experiments: [String]
    keywords: String
    organism: [String]
    technology_names: [String]
    schemas: [String]
    description: String
    name: String
    technology: [String]
    assay_types: [String]
    title: String
    dataset: String
    number_of_cells: Int
    sequencing: String
    normalization: String
    clustering: String
    marker_detection: String
    library_preparation: String
    total_celltypes: Int @cypher(
        statement: """
            MATCH (this)<-[r:celltype]->()
            RETURN distinct count(r) as total_celltypes;
        """
      )
    celltypes: [OntoTerm] @relationship(type: "celltype", direction: OUT)
    tissues: [OntoTerm] @relationship(type: "tissue", direction: OUT)
    diseases: [OntoTerm] @relationship(type: "disease", direction: OUT)
  }

  type Dataset {
    id: String
    title: String
    number_of_cells: Int
    uploaded: Date
    number_of_experiments: Int
    experiments: [Experiment] @relationship(type: "experiment", direction: OUT)
  }

  type Metric {
    id: String
    name: String
    count: Int
  }

  type DSDBRec {
    id: String
    title: String
    description: String
  }

  type OntoLite {
    id: String
    name: String
    count: Int
  }

  type Query {
    searchDSDB(query: String!): [DSDBRec]
    hasRelation(start: String!, end: String!): [Boolean] @cypher(
        statement: """
            MATCH (s:OntoTerm {id: $start})
            MATCH (e:OntoTerm {id: $end})
            CALL {
                with s,e
                CALL apoc.path.subgraphNodes(s, {
                    relationshipFilter: 'child>',
                    whitelistNodes: [e]
                })
                YIELD node
                return node

            UNION
                with s,e
                CALL apoc.path.subgraphNodes(e, {
                    relationshipFilter: 'child>',
                    whitelistNodes: [s]
                })
                YIELD node
                return node
            }
            return count(node) > 0 as hasRelation
        """
      )
    getDescendants(id: String!): [OntoTerm] @cypher(
        statement: """
            MATCH (o:OntoTerm {id: $id})-[:child*0..]->(r)-[:links]->(:Experiment)
            RETURN distinct r
        """
      )
    cellmetrics: [Metric] @cypher(
        statement: """
            MATCH (e:Experiment)-[r:celltype]->(o:OntoTerm)
            WITH distinct o.id as id, o.name as name, count(e) as count
            ORDER BY count DESC
            RETURN {id: id, name: name, count: count}
        """
      )
    tissuemetrics: [Metric] @cypher(
        statement: """
            MATCH (e:Experiment)-[r:tissue]->(o:OntoTerm)
            WITH distinct o.id as id, o.name as name, count(e) as count
            ORDER BY count DESC
            RETURN {id: id, name: name, count: count}
        """
      )
    diseasemetrics: [Metric] @cypher(
        statement: """
            MATCH (e:Experiment)-[r:disease]->(o:OntoTerm)
            WITH distinct o.id as id, o.name as name, count(e) as count
            ORDER BY count DESC
            RETURN {id: id, name: name, count: count}
        """
      )
    experimentmetrics: [Metric] @cypher(
        statement: """
            MATCH (e:Experiment)
            RETURN {id: d.id, name: 'experiments', count: count(e)}
        """
      )
    datametrics: [Metric] @cypher(
        statement: """
            MATCH (d:Dataset)
            RETURN {id: d.id, name: 'experiments', count: count(d)}
        """
      )
    organismmetrics: [Metric] @cypher(
        statement: """
            MATCH (e:Experiment)-[r:organism]->(o:OntoTerm)
            WITH distinct o.id as id, o.name as name, count(e) as count
            ORDER BY count DESC
            RETURN {id: id, name: name, count: count}
        """
      )
    totalcellmetrics: [Metric] @cypher(
        statement: """
            MATCH (e:Experiment)
            RETURN {id: 'total_cells', name: 'total_cells', count: sum(e.total_cells)}
        """
      )

    searchExperiments(
      celltypes: [String]
      diseases: [String]
      tissues: [String]
      organisms: [String]
      cellTypeOperation: String
      diseaseOperation: String
      tissueOperation: String
      organismOperation: String
      query: [String]
      queryOperation: String
    ): [Experiment]

    ontolitesearch(
      query: String!
      sources: [String!]
      limit: Int = 25
      offset: Int = 0
    ): [OntoLite] @cypher(
        statement: """
            MATCH (o:OntoTerm)
            WHERE o.source IN $sources
            AND toLower(o.name) CONTAINS toLower($query)
            RETURN distinct {id: o.id, name: o.name}
            SKIP $offset LIMIT $limit
        """
      )
  }
`;

// statement: """
// MATCH (o:OntoTerm)
// OPTIONAL MATCH (o)-[:links]->(d:Dataset)
// WHERE o.source IN $sources
// AND toLower(o.name) CONTAINS toLower($query)
// RETURN distinct {id: o.id, name: o.name, count: count(d)} as g
// ORDER BY g.count_datasets DESC
// SKIP $offset LIMIT $limit
// """

//
// MATCH (o:OntoTerm)-[]-(d:Dataset)
// WHERE o.source IN $sources
// AND toLower(o.name) CONTAINS toLower($query)
// With o
// CALL apoc.path.subgraphNodes(o, {
// relationshipFilter: 'parent>',
// labelFilter: '>OntoTerm'
// })
// YIELD node
// WHERE toLower(node.name) CONTAINS toLower($query)
// RETURN distinct {id: node.id, name: node.name}

module.exports = typeDefs;
