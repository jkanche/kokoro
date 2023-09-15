from neo4j import GraphDatabase


class graphManager:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def add_to_graph(self, query):
        with self.driver.session() as session:
            session.write_transaction(self._graph_tx, query)

    @staticmethod
    def _graph_tx(tx, query):
        result = tx.run(query)
        return result.single()
