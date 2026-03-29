#!/usr/bin/env bash
# Hub-M 双走廊模型：上传 plant、拓扑、挂接 ROS2 适配器；默认再下运输单并 trigger。
# 用法：
#   bash /home/klq/Final/curl_hub_m.sh              # T3 + T4
#   bash /home/klq/Final/curl_hub_m.sh --init-only  # 仅 T3（不创建运输单）
set -euo pipefail

BASE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
API="${OPENTCS_API:-http://localhost:55200/v1}"
MODEL="$BASE/opentcs_plant_model_hub_m.json"
INIT_ONLY=false
if [[ "${1:-}" == "--init-only" ]]; then
  INIT_ONLY=true
fi

echo "PUT plantModel from $MODEL"
curl -sS -X PUT "$API/plantModel" \
  -H "Content-Type: application/json" \
  --data-binary "@$MODEL"
echo

echo "POST topologyUpdateRequest"
curl -sS -X POST "$API/plantModel/topologyUpdateRequest" \
  -H "Content-Type: application/json" \
  -d '{"paths":["E-P0 --- E-P1","E-P1 --- E-P2","E-P2 --- M","M --- E-P3","M --- W-P3","W-P0 --- W-P1","W-P1 --- W-P2","W-P2 --- M"]}'
echo

for V in Vehicle-0001 Vehicle-0002; do
  echo "Setup $V (ROS2 adapter)"
  curl -sS -X PUT "$API/vehicles/$V/commAdapter/attachment?newValue=org.opentcs.ros2.adapter.Ros2CommunicationAdapterDescription"
  echo
  curl -sS -X PUT "$API/vehicles/$V/commAdapter/enabled?newValue=true"
  echo
  curl -sS -X PUT "$API/vehicles/$V/integrationLevel?newValue=TO_BE_UTILIZED"
  echo
  curl -sS -X PUT "$API/vehicles/$V/acceptableOrderTypes" \
    -H "Content-Type: application/json" \
    -d '{"acceptableOrderTypes":[{"name":"Move","priority":0}]}'
  echo
done

if [[ "$INIT_ONLY" == true ]]; then
  echo "(--init-only) 跳过运输单与 dispatcher/trigger。"
  exit 0
fi

echo "POST TOrder-HubM-E-1 (Vehicle-0001: Load -> Unload via M -> CHARGE)"
curl -sS -X POST "$API/transportOrders/TOrder-HubM-E-1" \
  -H "Content-Type: application/json" \
  -d '{
  "type": "Move",
  "intendedVehicle": "Vehicle-0001",
  "destinations": [
    { "locationName": "Location-E-Load", "operation": "Load" },
    { "locationName": "Location-E-Unload", "operation": "Unload" },
    { "locationName": "Location-E-Charge", "operation": "CHARGE" }
  ]
}'
echo

echo "POST TOrder-HubM-W-1 (Vehicle-0002: Load -> Unload via M -> CHARGE)"
curl -sS -X POST "$API/transportOrders/TOrder-HubM-W-1" \
  -H "Content-Type: application/json" \
  -d '{
  "type": "Move",
  "intendedVehicle": "Vehicle-0002",
  "destinations": [
    { "locationName": "Location-W-Load", "operation": "Load" },
    { "locationName": "Location-W-Unload", "operation": "Unload" },
    { "locationName": "Location-W-Charge", "operation": "CHARGE" }
  ]
}'
echo

echo "POST dispatcher/trigger"
curl -sS -X POST "$API/dispatcher/trigger"
echo

echo "Done. Peek orders:"
curl -sS "$API/transportOrders/TOrder-HubM-E-1" | head -n 40
echo "---"
curl -sS "$API/transportOrders/TOrder-HubM-W-1" | head -n 40
