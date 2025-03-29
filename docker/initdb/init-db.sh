#!/bin/bash

mysql -u root -p"$MYSQL_ROOT_PASSWORD" <<-EOSQL
    CREATE DATABASE IF NOT EXISTS \`$MYSQL_DB_NAME\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
    GRANT ALL PRIVILEGES ON \`$MYSQL_DB_NAME\`.* TO '$MYSQL_DB_USER'@'%';
    FLUSH PRIVILEGES;
EOSQL

echo "Cơ sở dữ liệu đã được khởi tạo thành công."