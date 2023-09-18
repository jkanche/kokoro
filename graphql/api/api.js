const { Neo4jGraphQL } = require("@neo4j/graphql");
const { ApolloServer } = require("apollo-server");
const neo4j = require("neo4j-driver");
const DsdbAPI = require('./dsdbAPI');
const SearchDB = require('./searchDB');
const resolvers = require('./resolvers');
const typeDefs = require('./model');

const driver = neo4j.driver(
    "bolt://" + process.env.NEO4J_SERVER + ":7687",
    neo4j.auth.basic(process.env.NEO4J_USER, process.env.NEO4J_PASS)
);

const neoSchema = new Neo4jGraphQL({ typeDefs, resolvers, driver });

const server = new ApolloServer({
    schema: neoSchema.schema,
    dataSources: () => {
        return {
            DsdbAPI: new DsdbAPI(),
            SearchDB: new SearchDB(),
        }
    },
    csrfPrevention: false,
    // context: ({ req }) => ({ req }),
});

server.listen(4000).then(({ url }) => {
    console.log(`🚀 Server ready at ${url}`);
});