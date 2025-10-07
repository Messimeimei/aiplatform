# 本地启动方式

docker compose -f docker-compose.dev.yml up --build

# 访问方式
## 打开 http://localhost:8000

# 手动部署服务器
在服务器上运行：
cd /root/aiplatform

## 1) 一键替换为个人版镜像地址
sed -i 's#^ \{2,4\}image: .*#    image: crpi-5vmn5esi06088rs1.cn-hangzhou.personal.cr.aliyuncs.com/messimeimei/meiss:latest#' docker-compose.yml

## 2) 登录个人版 ACR 并拉镜像（用访问凭证用户名/密码）
docker login crpi-5vmn5esi06088rs1.cn-hangzhou.personal.cr.aliyuncs.com -u '梅西的护腿板' -p '20040616wldn@YX'
docker pull  crpi-5vmn5esi06088rs1.cn-hangzhou.personal.cr.aliyuncs.com/messimeimei/meiss:latest

## 3) 启动
docker compose -f docker-compose.prod.yml down --remove-orphans || true
docker compose -f docker-compose.prod.yml up -d
## 4) 看容器与端口
docker ps -a
ss -tlnp | grep -E ':80|:8000' || true