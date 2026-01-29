array=(
  "dls-agent-log-producer"
  "dls-elasticsearch-proxy"
  "dls-flink-log-consumer"
  "dls-kafka-broker"
  "dls-log-monitoring-dashboard"
  "libraries"
)
for COMPONENT in "${array[@]}"
do
  cd "$COMPONENT" || exit
  chmod +x setup.sh
  ./setup.sh
  cd ..
done