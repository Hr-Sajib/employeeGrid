# Chat Agent Architecture

## System · from the browser to the database

![System architecture: browser, Caddy, the Docker container with routes, controllers, agent graph, tools and retrieval, external model APIs and the Postgres database](docs/architecture-system.png)

## Agent · every node as a container

![Agent graph: router, employee_data and documents branches, synthesizer with calculator, verifier, retry policy and shared state](docs/architecture-agent.png)
