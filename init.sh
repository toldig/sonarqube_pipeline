#!/bin/bash

# Set VM max map count
echo "Setting VM max map count"
sysctl -w vm.max_map_count=262144

# start postgresql as postgres and wait 5 sec to allow it to start up
echo "Start postgresql and wait 5 seconds"
su postgres -c '/usr/lib/postgresql/14/bin/postgres -D /etc/postgresql/14/main/ &'
sleep 5

# start sonarqube as sonar and wait until the health is GREEN
echo "Start sonarqube"
rm -rf /opt/sonarqube/temp
su sonar -c '/opt/sonarqube/bin/linux-x86-64/sonar.sh restart'

while true ; do
  curl -u admin:admin http://localhost:9000/api/system/health > health.dat
  STATUS=$(jq -r '.health' health.dat)
 
  echo "Status: $STATUS"
  if [ "$STATUS" == "GREEN" ]; then
    echo "Server is up"
    break
  fi
  echo "Server is down, waiting 5 seconds"
  sleep 5
done

# check if we are running in the pipeline or not
echo "Set project name to pipeline SHA"
if [[ -z "${CI_COMMIT_SHORT_SHA}" ]]; then
  # Set project name to default LOCALTEST and delete token for it, just in case
  CI_COMMIT_SHORT_SHA="LOCALTEST"
  curl -u admin:admin -X POST "http://localhost:9000/api/user_tokens/revoke" -d "name=$CI_COMMIT_SHORT_SHA"
fi

# generate token for project using the CI_COMMIT_SHORT_SHA variable
echo "Generate token for scanning project $CI_COMMIT_SHORT_SHA"
curl -u admin:admin -X POST http://localhost:9000/api/user_tokens/generate?name=$CI_COMMIT_SHORT_SHA > token.dat
TOKEN=$(jq -r '.token' token.dat)
# run scan

if [ $TOKEN == "null" ]; then
  echo "Invalid token, see token.dat:"
  cat token.dat
  exit 1
fi

echo "Run scanner with token: $TOKEN"
/opt/sonar-scanner/bin/sonar-scanner -Dsonar.projectKey=$CI_COMMIT_SHORT_SHA -Dsonar.login=$TOKEN -Dsonar.host.url=http://localhost:9000
