#!/usr/bin/env bash
SHELL_FOLDER=$(dirname $(readlink -f "$0"))
#export $(egrep -v '^#' env | xargs)
DOCKER_COMPOSE_FILE="docker-compose.yml"
DOCKER_COMPOSE_ENV="$SHELL_FOLDER/env"

DC_SERVICE_NAME=${1:-'ac'}
SERVICE_NAME="rcs_$DC_SERVICE_NAME"
SCALE=1
PRE_SCALE=$((SCALE+1))
echo '================== up new =================='
sudo docker-compose --env-file "$DOCKER_COMPOSE_ENV" -f "$SHELL_FOLDER/$DOCKER_COMPOSE_FILE" up -d --scale $DC_SERVICE_NAME=$PRE_SCALE --no-recreate
echo '============ stop and remove old ==========='
echo remove:
sudo docker stop -t 60 $(sudo docker ps --format "table {{.ID}}  {{.Names}}  {{.CreatedAt}}" | \
  grep $SERVICE_NAME | \
  sort -k3 | \
  awk -F  "  " '{print $2}' | head -$SCALE)
sudo docker container prune -f
echo '============== up new all =================='
sudo docker-compose --env-file "$DOCKER_COMPOSE_ENV" -f "$SHELL_FOLDER/$DOCKER_COMPOSE_FILE" up -d --scale $DC_SERVICE_NAME=$SCALE  --no-recreate
echo '================== done ===================='
sudo docker-compose --env-file "$DOCKER_COMPOSE_ENV" -f "$SHELL_FOLDER/$DOCKER_COMPOSE_FILE" ps --all
echo '================== log ====================='
sleep 1s
sudo docker-compose --env-file "$DOCKER_COMPOSE_ENV" -f "$SHELL_FOLDER/$DOCKER_COMPOSE_FILE" logs --tail 10 $DC_SERVICE_NAME