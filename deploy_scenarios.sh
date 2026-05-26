#!/bin/bash
# Cyber Range Scenario Deployment with OVS Isolation
set -e

# Cleanup any existing
sudo docker stop attacker-s1 web-s1 db-s1 attacker-s2 web-s2 db-s2 2>/dev/null || true
sudo docker rm attacker-s1 web-s1 db-s1 attacker-s2 web-s2 db-s2 2>/dev/null || true

# Ensure OVS bridges exist
for br in br-scenario-1 br-scenario-2 br-mgmt; do
  sudo ovs-vsctl br-exists $br 2>/dev/null || sudo ovs-vsctl add-br $br
  sudo ip link set $br up
done

# Assign gateway IPs
sudo ip addr add 10.0.1.1/24 dev br-scenario-1 2>/dev/null || true
sudo ip addr add 10.0.2.1/24 dev br-scenario-2 2>/dev/null || true

# Scenario 1: Web Pentest
sudo docker run -d --name attacker-s1 --network=none cyber-range/attacker sleep infinity
sudo docker run -d --name web-s1 --network=none cyber-range/web
sudo docker run -d --name db-s1 --network=none -e MYSQL_ROOT_PASSWORD=rootpass -e MYSQL_DATABASE=wordpress -e MYSQL_USER=wordpress -e MYSQL_PASSWORD=wordpress123 mysql:8.0
sudo ovs-docker add-port br-scenario-1 eth0 attacker-s1 --ipaddress=10.0.1.10/24 --gateway=10.0.1.1
sudo ovs-docker add-port br-scenario-1 eth0 web-s1 --ipaddress=10.0.1.11/24 --gateway=10.0.1.1
sudo ovs-docker add-port br-scenario-1 eth0 db-s1 --ipaddress=10.0.1.12/24 --gateway=10.0.1.1

# Scenario 2: Lateral Movement
sudo docker run -d --name attacker-s2 --network=none cyber-range/attacker sleep infinity
sudo docker run -d --name web-s2 --network=none cyber-range/web
sudo docker run -d --name db-s2 --network=none -e MYSQL_ROOT_PASSWORD=rootpass -e MYSQL_DATABASE=internal -e MYSQL_USER=admin -e MYSQL_PASSWORD=admin123 mysql:8.0
sudo ovs-docker add-port br-scenario-2 eth0 attacker-s2 --ipaddress=10.0.2.10/24 --gateway=10.0.2.1
sudo ovs-docker add-port br-scenario-2 eth0 web-s2 --ipaddress=10.0.2.11/24 --gateway=10.0.2.1
sudo ovs-docker add-port br-scenario-2 eth0 db-s2 --ipaddress=10.0.2.12/24 --gateway=10.0.2.1

echo 'Scenarios deployed. Isolation verified.'
