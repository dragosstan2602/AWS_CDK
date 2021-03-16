#!/bin/bash

yum update -y
yum install httpd -y
service httpd start
chkconfig httpd on
echo "<html><h1>Welcome To My Webpage - $(hostname)</h1></html>" > /var/www/html/index.html