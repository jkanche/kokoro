const { DataSource } = require("apollo-datasource");
const neo4j = require("neo4j-driver");
const { OGM } = require("@neo4j/graphql-ogm");
const typeDefs = require("./model");

class SearchDB extends DataSource {
  constructor() {
    super();

    this.driver = neo4j.driver(
      "bolt://" + process.env.NEO4J_SERVER + ":7687",
      neo4j.auth.basic(process.env.NEO4J_USER, process.env.NEO4J_PASS)
    );

    this.ogm = new OGM({ typeDefs, driver: this.driver });
    this.Experiment = this.ogm.model("Experiment");
    this.Dataset = this.ogm.model("Dataset")

    this.selectionSet = `
            {
                id
                title
                description
                organism
                total_celltypes
                number_of_cells
                library_preparation
                technology
                technology_names
                schemas
                dataset
                tissues {
                    id
                    name
                }
                celltypes {
                    id
                    name
                }
                diseases {
                    id
                    name
                }
                assay_types
                experiments
                sequencing
                parent_dataset {
                  id
                  title
                  number_of_cells
                  uploaded
                  number_of_experiments
                }
            }
        `;

    this.Experiment.setSelectionSet(this.selectionSet);
    this.Dataset.setSelectionSet(`
      {
        id
        title
        number_of_cells
        uploaded
        number_of_experiments
      }
    `)

    this.datasources = {
      celltypes: ["Cell Ontology"],
      tissues: ["UBERON"],
      diseases: ["Human Disease Ontology", "Mondo Disease Ontology"],
      organism: ["Experimental Factor Ontology"],
    };
  }

  // for cache purposes
  async queryTypes(input, key) {
    let sources = this.datasources[key];

    let rfilter = 'child>|links>';
    if (key === "organism") {
      rfilter = 'links>';
    }

    let query = `
            MATCH (o:OntoTerm)
            where o.id in [${input}] OR 
            any(name in [${input}] WHERE o.name contains name)
            CALL apoc.path.subgraphNodes(o, {
                    relationshipFilter: '${rfilter}',
                    labelFilter: '/Experiment'
                })
            YIELD node
            RETURN distinct node.id as id;
        `;

    return await this.sendQuery(query);
  }

  // for cache purposes
  async queryFreeText(input) {
    let op = "contains";

    if (input.startsWith('"') || input.startsWith("'")) {
      input = ` ${input.substring(1, input.length - 1)} `;
    } else {
      input = input.toLowerCase();
    }

    input = input.replace(/'/g, "\\'");

    let query = `
                MATCH (e:Experiment)
                WHERE toLower(e.title) ${op} '${input}'
                OR toLower(e.name) ${op} '${input}'
                OR toLower(e.description) ${op} '${input}'
                OR toLower(e.id) ${op} '${input}'
                or toLower(e.keywords) ${op} '${input}'
                RETURN distinct e.id as id;
            `;

    return await this.sendQuery(query);
  }

  // for cache purposes
  async sendQuery(query) {
    var session = this.driver.session();
    let result_ids = [];

    await session
      .run(query)
      .then((result) => {
        result_ids = result.records.map((x) => x.get("id"));
        return result_ids;
      })
      .catch((error) => {
        console.log(error);
      })
      .then(() => session.close());

    return result_ids;
  }

  async getMatches(
    celltypes,
    diseases,
    tissues,
    organisms,
    cellTypeOperation = "OR",
    diseaseOperation = "OR",
    tissueOperation = "OR",
    organismOperation = "OR",
    query,
    queryOperation = "OR",
  ) {
    // ignore node ssl check
    process.env["NODE_TLS_REJECT_UNAUTHORIZED"] = 0;

    let data_ids = [];

    let search_types = {
      celltypes: [celltypes, cellTypeOperation],
      diseases: [diseases, diseaseOperation],
      tissues: [tissues, tissueOperation],
      organism: [organisms, organismOperation],
    };

    for (var i_st = 0; i_st < Object.keys(search_types).length; i_st++) {
      const ikey = Object.keys(search_types)[i_st];
      let [type, op] = search_types[ikey];

      if (type) {
        if (op == "OR") {
          let input = `'${type.join("','")}'`;

          let result = await this.queryTypes(input, ikey);

          if (data_ids.length == 0) {
            data_ids = result;
          } else {
            data_ids = result.filter((v) => data_ids.includes(v));
          }
        } else {
          for (var ix = 0; ix < type.length; ix++) {
            let x = type[ix];

            let result = await this.queryTypes(`'${x}'`, ikey);

            if (data_ids.length == 0) {
              data_ids = result;
            } else {
              data_ids = result.filter((v) => data_ids.includes(v));
            }
          }
        }
      }
    }

    if (query) {
      let query_ids = [];
      if (queryOperation === "OR") {
        for (var ix = 0; ix < query.length; ix++) {
          let x = query[ix];
          let result = await this.queryFreeText(x);
          query_ids = query_ids.concat(result);
        }
      } else {
        for (var ix = 0; ix < query.length; ix++) {
          let x = query[ix];
          let result = await this.queryFreeText(x);

          if (query_ids.length == 0) {
            query_ids = result;
          } else {
            query_ids = result.filter((v) => query_ids.includes(v));
          }
        }
      }

      if (data_ids.length == 0) {
        data_ids = query_ids;
      } else {
        data_ids = query_ids.filter((v) => data_ids.includes(v));
      }
    }

    // make ids unique
    data_ids = [...new Set(data_ids)];

    return data_ids
  }

  async searchExperiments({
    celltypes,
    diseases,
    tissues,
    organisms,
    cellTypeOperation = "OR",
    diseaseOperation = "OR",
    tissueOperation = "OR",
    organismOperation = "OR",
    query,
    queryOperation = "OR",
  }) {
    let data_ids = await this.getMatches(celltypes,
      diseases,
      tissues,
      organisms,
      cellTypeOperation,
      diseaseOperation,
      tissueOperation,
      organismOperation,
      query,
      queryOperation);

    const ds = await this.Experiment.find({
      where: {
        id_IN: data_ids,
      },
    });

    return ds;
  }
}

module.exports = SearchDB;
