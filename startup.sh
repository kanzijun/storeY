# startup.sh: NOTE!!! THIS NEEDS TO BE EDITED.

# Create network
docker network create storey-network

# Create container running redis
docker run --network storey-network --name storey-redis -d redis redis-server --appendonly yes


# Build and create container to send emails
pushd workerserver
docker build -t workerserver .
docker run --network storey-network --name storey-workerserver -d workerserver
popd


# Build and mysql server/table
docker run -d --name mysql-server --network storey-network -e MYSQL_ROOT_PASSWORD=secret mysql --default-authentication-plugin=mysql_native_password
winpty docker exec -it mysql-server bash
mysql -uroot -p
CREATE DATABASE mydb;
USE mydb;
CREATE TABLE tasks (
    id INT AUTO_INCREMENT NOT NULL PRIMARY KEY,
    task VARCHAR(50) NOT NULL,
    is_completed BOOL
);

# Build and create container for our definition webserver
pushd webserver
docker build -t webserver .
docker run --network storey-network --name storey-webserver -d -e FLASK_APP=webserver.py -p 5000:5000 webserver
popd


