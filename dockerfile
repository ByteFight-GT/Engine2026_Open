FROM python:3.12-slim

# Create groups
RUN groupadd player_a && groupadd player_b

RUN useradd -r -g player_a player_a_user
RUN useradd -r -g player_b player_b_user

# --- Set working directory ---
WORKDIR /app

COPY docker_requirements.txt .

# --- Install system dependencies ---
RUN apt-get update && apt-get install -y \
    libseccomp-dev \
    gcc \
    python3-dev \
    build-essential \
    libcap-dev \
    && rm -rf /var/lib/apt/lists/*

# --- Install Python dependencies ---
RUN apt-get update && apt-get install -y openssl
RUN pip install --no-cache-dir -r docker_requirements.txt

# Copy files
ARG GAMEPLAY_FOLDER=gameplay
COPY . /app/BotFightEngine

RUN truncate -s 0 /app/BotFightEngine/app.log || true
# Ensure player directories exist
RUN mkdir -p /app/BotFightEngine/game_env/game_subs/${GAMEPLAY_FOLDER}/player_a
RUN mkdir -p /app/BotFightEngine/game_env/game_subs/${GAMEPLAY_FOLDER}/player_b

# Set ownerships
RUN chown -R player_a_user:player_a /app/BotFightEngine/game_env/game_subs/${GAMEPLAY_FOLDER}/player_a
RUN chown -R player_b_user:player_b /app/BotFightEngine/game_env/game_subs/${GAMEPLAY_FOLDER}/player_b

# Set permissions
RUN chmod -R 755 /app/BotFightEngine
RUN chmod -R 770 /app/BotFightEngine/game_env/game_subs/${GAMEPLAY_FOLDER}/player_a
RUN chmod -R 770 /app/BotFightEngine/game_env/game_subs/${GAMEPLAY_FOLDER}/player_b

# Engine runs as root initially (optional), players drop privileges later
USER root
WORKDIR /app/BotFightEngine
CMD ["python","-u", "engine/server.py"]