#!/bin/bash

echo "重置MySQL root密码..."

# 停止MySQL服务
echo "停止MySQL服务..."
brew services stop mysql

# 等待服务停止
sleep 3

# 以安全模式启动MySQL
echo "以安全模式启动MySQL..."
mysqld_safe --skip-grant-tables &
MYSQL_PID=$!

# 等待MySQL启动
echo "等待MySQL启动..."
sleep 5

# 连接到MySQL并重置密码
echo "重置root密码..."
mysql -u root << 'MYSQL_SCRIPT'
USE mysql;

-- 对于MySQL 5.7.6及以上版本
UPDATE user SET authentication_string='' WHERE User='root';
-- 或者对于旧版本
-- UPDATE user SET Password=PASSWORD('123456') WHERE User='root';

FLUSH PRIVILEGES;
EXIT;
MYSQL_SCRIPT

if [ $? -eq 0 ]; then
    echo "✅ 密码重置成功!"
else
    echo "❌ 密码重置失败"
fi

# 停止安全模式的MySQL
echo "停止安全模式MySQL..."
kill $MYSQL_PID
sleep 3

# 正常启动MySQL
echo "正常启动MySQL..."
brew services start mysql

# 等待启动
sleep 5

# 测试新密码
echo "测试连接..."
mysql -u root -e "SELECT VERSION();"

if [ $? -eq 0 ]; then
    echo "✅ MySQL已正常运行，root密码为空"
else
    echo "❌ 连接测试失败"
fi