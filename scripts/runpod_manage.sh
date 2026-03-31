#!/bin/bash
# RunPod pod management script — start/stop/status/cost
# Usage:
#   bash scripts/runpod_manage.sh status    # check pod status
#   bash scripts/runpod_manage.sh stop      # stop pod (saves disk, stops billing GPU)
#   bash scripts/runpod_manage.sh start     # start pod
#   bash scripts/runpod_manage.sh cost      # show running cost

POD_ID="6rkqqlaxfwzix0"
API_KEY=$(cat ~/.runpod/config.toml | grep apikey | cut -d"'" -f2)
API="https://api.runpod.io/graphql"

case "$1" in
  status)
    curl -s -H "Content-Type: application/json" -H "api-key: $API_KEY" $API \
      -d '{"query": "{ pod(input: {podId: \"'$POD_ID'\"}) { id name desiredStatus runtime { uptimeInSeconds } machine { gpuDisplayName } } }"}' | python3 -m json.tool
    ;;
  stop)
    echo "Stopping pod $POD_ID..."
    curl -s -H "Content-Type: application/json" -H "api-key: $API_KEY" $API \
      -d '{"query": "mutation { podStop(input: {podId: \"'$POD_ID'\"}) { id desiredStatus } }"}' | python3 -m json.tool
    ;;
  start)
    echo "Starting pod $POD_ID..."
    curl -s -H "Content-Type: application/json" -H "api-key: $API_KEY" $API \
      -d '{"query": "mutation { podResume(input: {podId: \"'$POD_ID'\", gpuCount: 1}) { id desiredStatus } }"}' | python3 -m json.tool
    ;;
  cost)
    UPTIME=$(curl -s -H "Content-Type: application/json" -H "api-key: $API_KEY" $API \
      -d '{"query": "{ pod(input: {podId: \"'$POD_ID'\"}) { runtime { uptimeInSeconds } costPerHr } }"}' | python3 -c "import sys,json; d=json.load(sys.stdin)['data']['pod']; u=d['runtime']['uptimeInSeconds']; c=d['costPerHr']; print(f'Uptime: {u//3600}h {(u%3600)//60}m | Cost: \${u/3600*c:.2f} (\${c}/hr)')")
    echo "$UPTIME"
    ;;
  *)
    echo "Usage: $0 {status|stop|start|cost}"
    ;;
esac
