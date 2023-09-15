module.exports = {
  Query: {
    searchDSDB: (_, { query }, { dataSources }) => {
      return dataSources.DsdbAPI.searchDSDB({ query: query });
    },

    searchExperiments: async (
      _,
      {
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
      },
      { dataSources }
    ) => {
      return dataSources.SearchDB.searchExperiments({
        celltypes,
        diseases,
        tissues,
        organisms,
        cellTypeOperation,
        diseaseOperation,
        tissueOperation,
        organismOperation,
        query,
        queryOperation,
      });
    },
  },
};
