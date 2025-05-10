# System Patterns

## System Architecture
- The application is a Flask-based web service.
- It uses SQLAlchemy as an ORM for database interaction.
- The system is designed to be run in Docker containers.
- Configuration, especially for the database, is managed through environment variables.
- Two main bandit algorithm implementations:
    - `multi_armed_bandit.py`: Standard MAB.
    - `rank_multi_armed_bandit.py`: Ranked MAB.
- A `main.py` likely acts as an entry point or dispatcher based on the `BANDIT_MODE` environment variable.

## Key Technical Decisions
- **Database Abstraction**: SQLAlchemy allows for flexibility in choosing a database backend (SQLite for development/testing, PostgreSQL for production).
- **Containerization**: Docker simplifies deployment and environment consistency.
- **Environment-based Configuration**: Enhances flexibility and security by separating configuration from code.
- **Temporal Context**: Recommendations consider the time of day (morning, afternoon, evening) by appending a time bin to the profile hash.

## Design Patterns
- **Strategy Pattern (implied)**: The `BANDIT_MODE` variable suggests a way to switch between different bandit algorithm implementations.
- **Repository Pattern (via SQLAlchemy)**: Database interactions are managed through SQLAlchemy models and sessions, abstracting direct SQL.
- **RESTful API**: Endpoints are designed following REST principles for creating and retrieving resources.

## Component Relationships
- `docker-compose.yml`: Defines services, environment variables, and potentially a database service (e.g., PostgreSQL).
- `Dockerfile`: Specifies how to build the application's Docker image.
- `requirements.txt`: Lists Python dependencies.
- `Entidades_mab.py` / `entidades_rmab.py`: Define SQLAlchemy database models (Arm, BanditData, Tenant).
- `multi_armed_bandit.py` / `rank_multi_armed_bandit.py`: Contain the Flask application logic for each bandit type, including API endpoints and algorithm implementation.
- `.env.example`: Provides a template for environment variables.
