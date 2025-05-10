# Tech Context

## Technologies Used
- **Programming Language**: Python 3 (specifically python:3.11-slim as per .clinerules)
- **Web Framework**: Flask
- **ORM**: SQLAlchemy
- **Database**: SQLite (default), PostgreSQL (configurable)
- **Containerization**: Docker, Docker Compose
- **Libraries**:
    - `numpy` (for Thompson Sampling random number generation)
    - `flask-cors` (for Cross-Origin Resource Sharing)
    - `psycopg2-binary` (will be needed if using PostgreSQL)

## Development Setup
- The application is designed to be run via `docker-compose up`.
- Environment variables defined in `docker-compose.yml` and potentially overridden by a `.env` file control application behavior (e.g., `BANDIT_MODE`, database connection parameters).
- The `Dockerfile` specifies the build steps for the application image, including installing dependencies from `requirements.txt`.
- A `python:3.11-slim` base image is used for the Docker container.

## Technical Constraints
- Database configuration must be flexible to support at least SQLite and PostgreSQL.
- The choice between MAB and RMAB is determined at runtime by the `BANDIT_MODE` environment variable.
- The application should be self-contained within its Docker image with all necessary dependencies.

## Dependencies
- Key Python packages are listed in `requirements.txt`.
- The application depends on a running database instance (either SQLite file-based or a PostgreSQL server).
- If using PostgreSQL, the `postgres` service in `docker-compose.yml` is a dependency for the `app` service.
