# startup.sh: NOTE!!! THIS NEEDS TO BE EDITED.

# Create network
docker network create storey-network

# Create container running redis
# docker run --network storey-network --name storey-redis -d redis redis-server --appendonly yes



# Build and create container to send emails
# pushd workerserver
# docker build -t workerserver .
# docker run --network storey-network --name storey-workerserver -d workerserver
# popd


# Build and mysql server/table
docker run -d --name mysql-server --network storey-network -e MYSQL_ROOT_PASSWORD=secret mysql --default-authentication-plugin=mysql_native_password
winpty docker exec -it mysql-server bash
# mysql -uroot -p
# CREATE DATABASE mydb;
# USE mydb;
# CREATE TABLE stories (title VARCHAR(150), text VARCHAR(1000), current_ip_addr VARCHAR(20), state BOOLEAN);
# CREATE TABLE ip (title VARCHAR(150), ip_addr VARCHAR(20));


# Build and create container for our definition webserver
pushd webserver
docker build -t def_image .
docker run --network storey-network --name storey-webserver -d -e FLASK_APP=storey.py -p 5000:5000 def_image
popd


