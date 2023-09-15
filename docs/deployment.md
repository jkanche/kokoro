# Deployment notes

The API is currently set up on an EC2 instance. Here's a step-by-step guide for the EC2 setup:

## EC2 Setup

- Create a new EC2 instance with sufficient memory (at least 2GB) to run Docker.

- Install Docker and python

- Clone the repository to the EC2 instance.

- Execute the following Docker commands to spin up the containers:

```bash
docker compose build && docker compose up -d
```

## Initial Setup (Only for the First Time)

#### Step 1: Create the Ontology Graph

This step involves generating an ontology graph in the Neo4j graph database. The directory scripts/ontologies stores the most recently imported versions of the OBO files.

#### Step 2: Import Initial Datasets (Only on First Setup)

Important: This step should be performed only during the initial setup, as there is a CRON job with Celery that is automatically configured to index.

The tasks/importer.py script is responsible for this task. Run this Python script for the very first time to import the initial datasets into the system.