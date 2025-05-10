# Product Context

## Problem Solved
This project provides a recommendation engine that can be tailored to different tenants and user profiles. It aims to deliver relevant recommendations to end-users, improving engagement and user experience.

## How it Works
The system uses Multi-Armed Bandit (MAB) and Ranked Multi-Armed Bandit (RMAB) algorithms to determine the best recommendations. It tracks impressions (pulls) and interactions (rewards) to learn which items perform best for specific user profiles and contexts (e.g., time of day).

- **MAB**: Selects a single best item.
- **RMAB**: Selects a ranked list of K items.

The system exposes API endpoints for:
- Getting recommendations.
- Recording user clicks/interactions.
- Managing tenants and arms (recommendable items).

## User Experience Goals
- **For End Users**: Receive relevant and timely recommendations.
- **For Administrators/Developers**: Easily configure and deploy the recommendation service. Integrate with different database backends (SQLite, PostgreSQL) via environment variables.
