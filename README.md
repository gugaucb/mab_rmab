# Multi-Armed Bandit Project

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
<!-- Add build status badge once CI/CD is set up -->
<!-- [![Build Status](https://travis-ci.org/your_username/your_repository.svg?branch=main)](https://travis-ci.org/your_username/your_repository) -->

This project implements a Multi-Armed Bandit (MAB) and a Ranked Multi-Armed Bandit (RMAB) system using Thompson Sampling. It's designed for collaborative development and easy deployment with Docker.

## Project Objective

The main goal is to provide a flexible and extensible recommendation engine that can adapt to user preferences over time. It supports two modes:
1.  **Multi-Armed Bandit (MAB):** Recommends a single best item.
2.  **Ranked Multi-Armed Bandit (RMAB):** Recommends a ranked list of K items.

The system learns from user interactions (clicks) to optimize recommendations.

## How it Works

The application uses a Flask backend to serve API endpoints for getting recommendations and recording user clicks. It supports both SQLite and PostgreSQL databases for storing bandit data, configurable via environment variables.

-   **Thompson Sampling:** The core algorithm used for balancing exploration (trying new arms) and exploitation (choosing known good arms).
-   **Contextual Bandits:** The system incorporates a simple time-based context (morning, afternoon, evening) to tailor recommendations.
-   **Ranked Bandits (RMAB):** Extends the MAB concept to recommend an ordered list of items, learning the best item for each position in the list.

## Project Structure

```
bandit_project/
├── bandits/
│   ├── __init__.py
│   ├── multi_armed_bandit.py   # MAB implementation
│   └── rank_multi_armed_bandit.py # RMAB implementation
├── instance/                     # Default location for SQLite DBs
│   └── (database files will be created here if using SQLite)
├── main.py                       # Main application entry point
├── Dockerfile                    # For building the Docker image
├── docker-compose.yml            # For running the application with Docker Compose
├── .env.example                  # Example environment variables
├── requirements.txt              # Python dependencies
└── README.md                     # This file
```

## Local Execution

### Prerequisites
- Python 3.11+
- Pip

### Setup
1.  **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd bandit_project
    ```
2.  **Create and activate a virtual environment (recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```
3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Set up environment variables:**
    Copy `.env.example` to `.env` and configure it:
    ```bash
    cp .env.example .env
    # Edit .env with your desired settings
    # For example, to use the ranked bandit with SQLite:
    # BANDIT_MODE=rank_multi_armed_bandit
    # DB_TYPE=sqlite
    # DB_PATH=./instance/my_ranked_bandit.db # Path relative to project root for local run
    ```
    *Note: For local execution without Docker, `DB_PATH` for SQLite should be a path accessible by your local machine, e.g., `instance/recommender.db`.*

5.  **Run the application:**
    The `main.py` script will load the appropriate bandit class based on the `BANDIT_MODE` environment variable.
    ```bash
    python main.py
    ```
    The application will start, typically on `http://127.0.0.1:5000` for `multi_armed_bandit` or `http://127.0.0.1:5001` for `rank_multi_armed_bandit` (ports are defined in the respective bandit files).

## Docker Execution

### Prerequisites
- Docker
- Docker Compose

### Build and Run with Docker Compose
1.  **Set up environment variables:**
    Copy `.env.example` to `.env` and configure it for Docker.
    ```bash
    cp .env.example .env
    # Edit .env. For example:
    # BANDIT_MODE=multi_armed_bandit
    # DB_TYPE=sqlite
    # DB_PATH=/app/instance/recommender.db # Path inside the container
    ```
    If using PostgreSQL, uncomment and set the `DB_URL`, `DB_USER`, `DB_PASS`, and `DB_NAME` variables. Ensure the `postgres` service in `docker-compose.yml` is also configured and not commented out.

2.  **Run with Docker Compose:**
    ```bash
    docker-compose up --build
    ```
    This will build the image and start the application and PostgreSQL container (if configured). The application will be accessible on `http://localhost:80` (or the port mapped in `docker-compose.yml`).

### Running a Pre-built Image from DockerHub (Example)
*(Assuming the image is published as `yourusername/bandit-project`)*

1.  **Pull the image:**
    ```bash
    docker pull yourusername/bandit-project:latest
    ```
2.  **Run the image:**

    **Using SQLite (with a host volume for persistence):**
    ```bash
    docker run -d -p 80:80 \
      -e BANDIT_MODE="multi_armed_bandit" \
      -e DB_TYPE="sqlite" \
      -e DB_PATH="/app/instance/recommender.db" \
      -v $(pwd)/my_sqlite_data:/app/instance \
      --name bandit_app \
      yourusername/bandit-project:latest
    ```
    *(This mounts a local directory `my_sqlite_data` to `/app/instance` in the container where the SQLite DB will be stored.)*

    **Using PostgreSQL (assuming a separate PostgreSQL container is running and accessible):**
    Create an `.env` file (e.g., `db.env`):
    ```
    BANDIT_MODE=multi_armed_bandit
    DB_TYPE=postgresql
    DB_URL=your_postgres_host_ip_or_docker_service_name
    DB_USER=your_user
    DB_PASS=your_password
    DB_NAME=your_db
    ```
    Then run:
    ```bash
    docker run -d -p 80:80 \
      --env-file db.env \
      --name bandit_app \
      yourusername/bandit-project:latest
    ```

## API Endpoints & Examples (cURL)

The application exposes the following endpoints. The base URL will be `http://localhost` (if using Docker with default port 80) or `http://127.0.0.1:PORT` (for local execution, where PORT is 5000 or 5001).

### 1. Create Tenant
   - **Endpoint:** `/tenant`
   - **Method:** `POST`
   - **Body (JSON):** `{"tenant_id": "tenant_A"}`
   - **cURL Example:**
     ```bash
     curl -X POST -H "Content-Type: application/json" -d '{"tenant_id": "tenant_A"}' http://localhost/tenant
     ```

### 2. Create Arm
   - **Endpoint:** `/arm`
   - **Method:** `POST`
   - **Body (JSON):** `{"tenant_id": "tenant_A", "arm_id": "item_1", "name": "Cool Item 1"}`
   - **cURL Example:**
     ```bash
     curl -X POST -H "Content-Type: application/json" -d '{"tenant_id": "tenant_A", "arm_id": "item_1", "name": "Cool Item 1"}' http://localhost/arm
     curl -X POST -H "Content-Type: application/json" -d '{"tenant_id": "tenant_A", "arm_id": "item_2", "name": "Awesome Item 2"}' http://localhost/arm
     ```

### 3. Get Recommendation
   - **Endpoint:** `/recommendation`
   - **Method:** `GET`
   - **Query Parameters:**
     - `tenant_id`: (string, required)
     - `profile_hash`: (string, required) A unique identifier for the user profile/context.
     - `k`: (integer, optional, for RMAB only) Number of ranked recommendations to return. Defaults to 3.
   - **cURL Examples:**

     **For MAB (BANDIT_MODE=multi_armed_bandit):**
     ```bash
     curl "http://localhost/recommendation?tenant_id=tenant_A&profile_hash=user123_contextXYZ"
     ```
     *Expected Response (MAB):* `{"arm_id": "item_X", "name": "Some Item X"}`

     **For RMAB (BANDIT_MODE=rank_multi_armed_bandit):**
     ```bash
     curl "http://localhost/recommendation?tenant_id=tenant_A&profile_hash=user456_contextABC&k=2"
     ```
     *Expected Response (RMAB):*
     ```json
     [
       {"arm_id": "item_Y", "name": "Some Item Y", "position": 1},
       {"arm_id": "item_Z", "name": "Another Item Z", "position": 2}
     ]
     ```

### 4. Record Click
   - **Endpoint:** `/click`
   - **Method:** `POST`
   - **Body (JSON):**
     - **For MAB:** `{"tenant_id": "tenant_A", "profile_hash": "user123_contextXYZ", "arm_id": "item_X", "clicked": true}`
     - **For RMAB:** `{"tenant_id": "tenant_A", "profile_hash": "user456_contextABC", "arm_id": "item_Y", "position": 1}` (implicitly `clicked: true`)
   - **cURL Examples:**

     **For MAB:**
     ```bash
     curl -X POST -H "Content-Type: application/json" \
       -d '{"tenant_id": "tenant_A", "profile_hash": "user123_contextXYZ", "arm_id": "item_X", "clicked": true}' \
       http://localhost/click
     ```

     **For RMAB:**
     ```bash
     curl -X POST -H "Content-Type: application/json" \
       -d '{"tenant_id": "tenant_A", "profile_hash": "user456_contextABC", "arm_id": "item_Y", "position": 1}' \
       http://localhost/click
     ```

## Future Enhancements
-   Implement automated tests (unit, integration).
-   More sophisticated contextual features.
-   Support for other MAB algorithms.
-   Scalability improvements for high-traffic scenarios.
-   CI/CD pipeline for automated builds and deployments.

## License
This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details (though a separate LICENSE.md file is not created by this prompt, the MIT license is declared).
