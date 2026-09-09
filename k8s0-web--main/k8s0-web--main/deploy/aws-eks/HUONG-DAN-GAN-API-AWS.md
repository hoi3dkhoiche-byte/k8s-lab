# Hướng Dẫn Chi Tiết: Gắn Endpoint & Khóa API AWS Vào Hệ Thống

Tài liệu này hướng dẫn bạn chính xác **chỗ lấy thông tin trên AWS Console** và **chỗ dán thông tin vào hệ thống** sau khi bạn đã bấm tạo xong các dịch vụ trên AWS (S3, ElastiCache, RDS PostgreSQL, RDS MySQL, DocumentDB).

> **Nguyên tắc thiết kế:** Mã nguồn đã được chuẩn hóa để tự động đọc toàn bộ cấu hình từ **Biến Môi Trường (Environment Variables)**. Bạn **KHÔNG CẦN CHỈNH SỬA BẤT KỲ FILE CODE PYTHON NÀO**. Bạn chỉ cần dán các endpoint vào đúng 2 file cấu hình dưới đây!

---

## BƯỚC 1: LẤY THÔNG TIN TỪ AWS CONSOLE

Sau khi tạo xong các dịch vụ trên AWS, hãy copy các thông tin sau:

### 1. Amazon S3 (Lưu trữ ảnh)
1. Vào AWS Console → **Amazon S3** → Nhấp vào bucket vừa tạo.
2. Lấy **Bucket Name** (Ví dụ: `bida-caocap-images-prod`).
3. Lấy **AWS Region** (Ví dụ: `ap-southeast-1` - Singapore).
4. *(Tùy chọn)* Nếu bạn có tạo **CloudFront** trỏ vào S3:
   - Vào **CloudFront** → Lấy **Distribution domain name** (Ví dụ: `https://d123456789.cloudfront.net`).

---

### 2. Amazon ElastiCache for Redis (Real-Time Trading & Inventory)
1. Vào AWS Console → **Amazon ElastiCache** → **Redis clusters**.
2. Nhấp vào tên cụm Redis của bạn.
3. Tìm mục **Primary endpoint** và copy (Ví dụ: `master.bida-redis.xxxx.apse1.cache.amazonaws.com:6379`).
4. Chuỗi kết nối hoàn chỉnh sẽ là:
   - Nếu có bật mã hóa TLS (khuyến nghị): `rediss://master.bida-redis.xxxx.apse1.cache.amazonaws.com:6379/0`
   - Nếu không bật TLS: `redis://master.bida-redis.xxxx.apse1.cache.amazonaws.com:6379/0`

---

### 3. Amazon RDS PostgreSQL (User Service DB)
1. Vào AWS Console → **Amazon RDS** → **Databases** → Nhấp vào instance PostgreSQL.
2. Tìm mục **Connectivity & security** → Copy **Endpoint** và **Port** (Mặc định: 5432).
3. Chuỗi kết nối chuẩn:
   ```text
   postgresql://<db_user>:<db_password>@<endpoint-rds-postgres>:5432/<db_name>
   ```
   *Ví dụ:* `postgresql://dbadmin:MatKhauManh123@bida-pg.c123456.ap-southeast-1.rds.amazonaws.com:5432/user_db`

---

### 4. Amazon RDS MySQL (Order & Inventory DB)
1. Vào AWS Console → **Amazon RDS** → **Databases** → Nhấp vào instance MySQL.
2. Tìm mục **Connectivity & security** → Copy **Endpoint** và **Port** (Mặc định: 3306).
3. Chuỗi kết nối chuẩn (dùng driver `pymysql`):
   ```text
   mysql+pymysql://<db_user>:<db_password>@<endpoint-rds-mysql>:3306/<db_name>
   ```
   *Ví dụ:* `mysql+pymysql://dbadmin:MatKhauManh123@bida-mysql.c123456.ap-southeast-1.rds.amazonaws.com:3306/order_db`

---

### 5. Amazon DocumentDB (Catalog DB)
1. Vào AWS Console → **Amazon DocumentDB** → **Clusters** → Nhấp vào cụm DocumentDB.
2. Tìm mục **Connectivity & security** → Copy dòng lệnh kết nối mẫu (Cluster endpoint).
3. Chuỗi kết nối chuẩn (đã tích hợp chứng chỉ AWS SSL có sẵn trong container):
   ```text
   mongodb://<docdb_user>:<docdb_password>@<endpoint-documentdb>:27017/catalog_db?tls=true&tlsCAFile=/app/certs/global-bundle.pem&replicaSet=rs0&readPreference=secondaryPreferred&retryWrites=false
   ```
   *Ví dụ:* `mongodb://docdbadmin:MatKhauDocDB123@bida-docdb.c123456.ap-southeast-1.docdb.amazonaws.com:27017/catalog_db?tls=true&tlsCAFile=/app/certs/global-bundle.pem&replicaSet=rs0&readPreference=secondaryPreferred&retryWrites=false`

---

## BƯỚC 2: DÁN CÁC THÔNG TIN VÀO CODEBASE

### Cách 1: Khi Triển Khai Lên Amazon EKS (Khuyến Nghị)

Mở 2 file sau trong thư mục `deploy/aws-eks/`:

#### 1. File `deploy/aws-eks/02-configmap.yaml`
Dán thông tin ElastiCache và S3 vào các dòng sau:
```yaml
  # Dán Primary Endpoint của ElastiCache Redis:
  REDIS_URL: "rediss://master.bida-redis.xxxxxx.apse1.cache.amazonaws.com:6379/0"

  # Dán tên Bucket S3 và Region:
  S3_BUCKET_NAME: "bida-caocap-images-prod"
  AWS_REGION: "ap-southeast-1"
  S3_REGION: "ap-southeast-1"

  # Dán domain CloudFront CDN (nếu có, nếu không để trống ""):
  S3_PUBLIC_URL_PREFIX: "https://d123456789.cloudfront.net"
```

#### 2. File `deploy/aws-eks/03-secrets.yaml`
Dán thông tin 3 cơ sở dữ liệu và mật khẩu vào các dòng sau:
```yaml
  # Đổi chuỗi ký token JWT tuỳ ý:
  SECRET_KEY: "chuoi-secret-key-ngau-nhien-rat-bao-mat-2024"

  # Dán chuỗi kết nối RDS PostgreSQL:
  POSTGRES_URL: "postgresql://dbadmin:MatKhauManh123@bida-pg.c123456.ap-southeast-1.rds.amazonaws.com:5432/user_db"

  # Dán chuỗi kết nối RDS MySQL:
  MYSQL_URL: "mysql+pymysql://dbadmin:MatKhauManh123@bida-mysql.c123456.ap-southeast-1.rds.amazonaws.com:3306/order_db"

  # Dán chuỗi kết nối Amazon DocumentDB:
  MONGO_URL: "mongodb://docdbadmin:MatKhauDocDB123@bida-docdb.c123456.ap-southeast-1.docdb.amazonaws.com:27017/catalog_db?tls=true&tlsCAFile=/app/certs/global-bundle.pem&replicaSet=rs0&readPreference=secondaryPreferred&retryWrites=false"
```

---

### Cách 2: Khi Chạy Thử Nghiệm Ngoài Local Nhưng Kết Nối Tới AWS

Nếu bạn muốn chạy `docker-compose` trên máy tính cá nhân nhưng kết nối trực tiếp vào AWS RDS / ElastiCache / S3:
1. Copy file `.env.example` thành `.env`:
   ```bash
   cp .env.example .env
   ```
2. Điền các giá trị trên vào file `.env`.
3. Chạy lệnh:
   ```bash
   docker-compose up -d
   ```

---

## BƯỚC 3: TRIỂN KHAI VÀ KHỞI TẠO DỮ LIỆU LÊN AWS EKS

Sau khi đã điền xong 2 file ở Bước 2, bạn mở Terminal chạy các lệnh sau:

### 1. Áp Dụng Cấu Hình Lên EKS
```bash
# 1. Tạo namespace
kubectl apply -f deploy/aws-eks/01-namespace.yaml

# 2. Nạp ConfigMap và Secrets vừa chỉnh sửa
kubectl apply -f deploy/aws-eks/02-configmap.yaml
kubectl apply -f deploy/aws-eks/03-secrets.yaml

# 3. Tạo ServiceAccount (IRSA cho S3)
kubectl apply -f deploy/aws-eks/04-serviceaccounts.yaml

# 4. Deploy Data API Service
kubectl apply -f deploy/aws-eks/05-data-api-service.yaml

# 5. Deploy toàn bộ Microservices
kubectl apply -f deploy/aws-eks/06-microservices.yaml

# 6. Deploy Frontend và API Gateway
kubectl apply -f deploy/aws-eks/07-frontend-gateway.yaml

# 7. Cấp phát AWS Application Load Balancer (ALB)
kubectl apply -f deploy/aws-eks/08-ingress-alb.yaml
```

---

### 2. Nạp Dữ Liệu Khởi Tạo (Admin, Sản Phẩm Mẫu, Kho Hàng Real-Time)
Chạy kịch bản nạp dữ liệu một lần duy nhất:
```bash
kubectl apply -f deploy/aws-eks/job-seed.yaml
```
Lệnh này sẽ tự động:
- Tạo tài khoản **`admin / admin123`** trên Amazon RDS PostgreSQL.
- Nạp danh mục và các sản phẩm mẫu vào Amazon DocumentDB.
- Nạp số lượng tồn kho khả dụng vào **Amazon ElastiCache for Redis**.

---

## BƯỚC 4: LẤY LINK TRUY CẬP WEBSITE
Chạy lệnh:
```bash
kubectl get ingress -n bida
```
Bạn sẽ thấy cột **`ADDRESS`** dạng:
`k8s-bida-bidaingr-xxxxxxxx.ap-southeast-1.elb.amazonaws.com`

👉 Truy cập đường link này trên trình duyệt:
- Website bán hàng: `http://k8s-bida-bidaingr-xxxxxxxx.ap-southeast-1.elb.amazonaws.com`
- Trang đăng nhập: `http://k8s-bida-bidaingr-xxxxxxxx.ap-southeast-1.elb.amazonaws.com/login.html` (Đăng nhập: `admin` / `admin123` để vào trang quản trị).
