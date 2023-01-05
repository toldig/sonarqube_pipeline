### Sonarqube pipeline with custom image

Used debian parent image  
```
docker pull debian:latest
```

Create **app** directory, enter it, put everything here  
We will need to install these in the container:  
- custom scripts  
- download [sonar-scanner-cli](https://binaries.sonarsource.com/?prefix=Distribution/sonar-scanner-cli/) and extract it and rename directory to sonar-scanner  
- download [sonarqube](https://www.sonarsource.com/products/sonarqube/downloads/) and extract it and rename directory to sonarqube  
```
mkdir app
cd app
```

Custom scripts are:  
- [init.sh](init.sh): starts sonarqube and scans local project  
- [sonarqube.py](sonarqube.py): saves the scan results to sonarscan.csv file  

Run debian image and map the **app** directory within the container to /app  
```
docker run --privileged -it --rm -v "$(pwd):/app" debian:latest
```

Copy files to the opt directory  
```
mkdir /opt/custom-scripts
cp /app/init.sh /opt/custom-scripts/
cp /app/sonarqube.py /opt/custom-scripts/
cp -R /app/sonar-scanner /opt/
cp -R /app/sonarqube /opt/
```

Create user sonar with stongpassword  
```
adduser sonar
```

Change owner of the sonarqube directory  
```
chown -R sonar:sonar /opt/sonarqube/
```

Install some tools we need  
```
apt update

apt install curl -y
apt install jq -y
apt install openjdk-11-jdk -y
apt install procps -y

apt install python3 -y
apt install python3-pip -y
pip3 install requests

curl -sL https://deb.nodesource.com/setup_14.x | bash -
apt install nodejs -y
```

Do **NOT** close this terminal, open another one, and get the container ID  
```
docker ps
```

Commit the changes to a new image  
```
docker container commit 324d957b3f01 sonarqubecustom:latest
```

Or if you have only one container running  
```bash
docker container commit $(docker ps -q) sonarqubecustom:latest
```

Tag and push image to your repo  
```
docker image tag sonarqubecustom:latest harbor.xxxxxxxxx.xxx/xxxx/sonarqubecustom:latest
docker image push harbor.xxxxxxxxx.xxx/xxxx/sonarqubecustom:latest
```

For testing, put a project in **app** directory, enter project directory and execute custom scripts  
```
cd /app/project
/opt/custom-scripts/init.sh
/opt/custom-scripts/sonarqube.py

```

If you need to troubleshoot sonarqube, check out the logs at /opt/sonarqube/logs  
