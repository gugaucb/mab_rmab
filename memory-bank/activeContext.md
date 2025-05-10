# Active Context

## Current Work Focus
The immediate task is to modify `multi_armed_bandit.py` and `rank_multi_armed_bandit.py` to use database configurations provided via environment variables, as defined in `docker-compose.yml`. This involves:
1. Reading database-related environment variables (DB_TYPE, DB_PATH, DB_URL, DB_USER, DB_PASS, DB_NAME).
2. Constructing the `SQLALCHEMY_DATABASE_URI` dynamically based on these variables.
3. Ensuring the application correctly connects to either SQLite or PostgreSQL.

## Recent Changes
- Initializing the Memory Bank by creating `projectbrief.md`, `productContext.md`, `systemPatterns.md`, and `techContext.md`.

## Next Steps
1. **Modify `multi_armed_bandit.py`**:
    - Import `os`.
    - Read environment variables for DB configuration.
    - Dynamically set `app.config['SQLALCHEMY_DATABASE_URI']`.
2. **Modify `rank_multi_armed_bandit.py`**:
    - Import `os`.
    - Read environment variables for DB configuration.
    - Dynamically set `app.config['SQLALCHEMY_DATABASE_URI']`.
    - Note: This file uses a different SQLite database name (`recommender_rmab.db`). The DB_PATH for SQLite should be respected, but the filename itself might need to be appended or handled if `DB_PATH` is just a directory. The `docker-compose.yml` specifies `DB_PATH:-/app/instance/recommender.db`. This needs careful handling for RMAB's separate DB. Perhaps `DB_PATH_MAB` and `DB_PATH_RMAB` or a similar strategy will be needed if both run in the same container and need separate SQLite files. For now, assume `DB_PATH` refers to the MAB database path, and RMAB will need a distinct path, potentially `DB_PATH_RMAB` or by appending `_rmab` to the `DB_PATH`'s filename. The current task is to use the *existing* env vars from `docker-compose.yml`. The `DB_PATH` in `docker-compose.yml` is `/app/instance/recommender.db`. The RMAB file currently hardcodes `sqlite:///recommender_rmab.db`. This implies it should be `/app/instance/recommender_rmab.db` if `DB_TYPE` is sqlite.
3. **Update `main.py` (Potentially)**: If database initialization logic is centralized or shared, `main.py` might also need changes. However, the current task focuses on the bandit files themselves.
4. **Update `Dockerfile` (Potentially)**: Ensure `psycopg2-binary` is in `requirements.txt` if PostgreSQL support is to be fully functional. (Checking `requirements.txt` content will be a good step).
5. **Update `.clinerules`**: If new project-wide patterns emerge.
6. **Update `progress.md`**: After completing the modifications.

## Active Decisions and Considerations
- How to handle the different SQLite database file names for MAB and RMAB when `DB_TYPE` is `sqlite`. The `docker-compose.yml` defines `DB_PATH` which seems to point to a single file.
    - Option A: Assume `DB_PATH` is a directory if `DB_TYPE=sqlite`, and the specific filenames (`recommender.db`, `recommender_rmab.db`) are appended.
    - Option B: Introduce a new environment variable like `DB_PATH_RMAB`. (Out of scope for "use existing env vars").
    - Option C: The `main.py` (if it's a dispatcher) might set different DB URIs before loading the respective bandit app.
    - **Chosen Approach for now**: For `multi_armed_bandit.py`, use `DB_PATH`. For `rank_multi_armed_bandit.py`, if `DB_TYPE=sqlite`, construct the path like `os.path.join(os.path.dirname(DB_PATH), 'recommender_rmab.db')` if `DB_PATH` is a full file path, or simply use a fixed name if `DB_PATH` is just a directory. Given `DB_PATH:-/app/instance/recommender.db` in `docker-compose.yml`, the RMAB path should be `/app/instance/recommender_rmab.db`.
- Ensure that if `DB_TYPE` is `postgresql`, the connection string is correctly formed using `DB_URL`, `DB_USER`, `DB_PASS`, and `DB_NAME`.
