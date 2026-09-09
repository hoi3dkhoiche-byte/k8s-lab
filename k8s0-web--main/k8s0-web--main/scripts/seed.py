import os
import asyncio
from datetime import datetime
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Numeric, Text, DateTime, Enum as SQLEnum
from sqlalchemy.orm import sessionmaker
# pyrefly: ignore [missing-import]
from motor.motor_asyncio import AsyncIOMotorClient
# pyrefly: ignore [missing-import]
import passlib.context
import enum

MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://admin:admin123@localhost:27017/')
MYSQL_URL = os.environ.get('MYSQL_URL', 'mysql+pymysql://admin:admin123@localhost:3306/order_db')
POSTGRES_URL = os.environ.get('POSTGRES_URL', 'postgresql://admin:admin123@localhost:5432/user_db')

pwd_context = passlib.context.CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

products_data = [
    {
        "name": "Gậy Lỗ Predator SP2 Revo",
        "category": "cues",
        "price": 18500000,
        "description": "Gậy lỗ Predator SP2 Revo với công nghệ ngọn carbon siêu nhẹ và bền, cho độ chính xác tuyệt đối.",
        "desc": "Gậy lỗ Predator SP2 Revo với công nghệ ngọn carbon siêu nhẹ và bền, cho độ chính xác tuyệt đối.",
        "img": "images/cue-predator-revo.jpg",
        "images": ["images/cue-predator-revo.jpg"],
        "specs": {"weight": "19oz", "tip": "Predator Victory (Soft)", "joint": "Uni-Loc"},
        "tags": ["predator", "revo", "carbon"],
        "stock": 10,
        "is_featured": True
    },
    {
        "name": "Gậy Lỗ Mezz AXI-151",
        "category": "cues",
        "price": 14500000,
        "description": "Mezz AXI-151 kết hợp vẻ đẹp truyền thống và công nghệ hiện đại. Cân bằng hoàn hảo.",
        "desc": "Mezz AXI-151 kết hợp vẻ đẹp truyền thống và công nghệ hiện đại. Cân bằng hoàn hảo.",
        "img": "images/cue-mezz-axi.jpg",
        "images": ["images/cue-mezz-axi.jpg"],
        "specs": {"weight": "19.5oz", "tip": "Kamui (Medium)", "joint": "Wavy Joint"},
        "tags": ["mezz", "wood"],
        "stock": 8,
        "is_featured": True
    },
    {
        "name": "Gậy Lỗ Cuetec Cynergy Breach",
        "category": "cues",
        "price": 16200000,
        "description": "Gậy bida lỗ Cuetec Cynergy ngọn carbon composite cao cấp lực phát bóng cực đầm và chính xác.",
        "desc": "Gậy bida lỗ Cuetec Cynergy ngọn carbon composite cao cấp lực phát bóng cực đầm và chính xác.",
        "img": "images/cue-cuetec-cynergy.jpg",
        "images": ["images/cue-cuetec-cynergy.jpg"],
        "specs": {"weight": "19oz", "tip": "Tiger Sniper", "joint": "3/8-14"},
        "tags": ["cuetec", "cynergy"],
        "stock": 6,
        "is_featured": True
    },
    {
        "name": "Gậy Lỗ Lucasi Custom LZC",
        "category": "cues",
        "price": 11500000,
        "description": "Lucasi Custom chế tác hoa văn tinh xảo từ gỗ quý, cảm giác đánh chắc chắn, kiểm soát bi cái tối ưu.",
        "desc": "Lucasi Custom chế tác hoa văn tinh xảo từ gỗ quý, cảm giác đánh chắc chắn, kiểm soát bi cái tối ưu.",
        "img": "images/cue-lucasi-custom.jpg",
        "images": ["images/cue-lucasi-custom.jpg"],
        "specs": {"weight": "19oz", "tip": "Kamui Brown", "joint": "Uni-Loc Quick-Release"},
        "tags": ["lucasi", "custom"],
        "stock": 5,
        "is_featured": False
    },
    {
        "name": "Ngọn Predator Revo 12.4 Carbon",
        "category": "accessories",
        "price": 11000000,
        "description": "Ngọn Revo 12.4mm bằng sợi carbon vũ trụ, độ bạt thấp kỷ lục, không bao giờ cong vênh.",
        "desc": "Ngọn Revo 12.4mm bằng sợi carbon vũ trụ, độ bạt thấp kỷ lục, không bao giờ cong vênh.",
        "img": "images/shaft-carbon-revo.jpg",
        "images": ["images/shaft-carbon-revo.jpg"],
        "specs": {"tip_size": "12.4mm", "material": "Carbon Composite", "joint": "Uni-Loc"},
        "tags": ["predator", "shaft", "carbon"],
        "stock": 20,
        "is_featured": True
    },
    {
        "name": "Lơ Kamui Roku (Kamui Chalk)",
        "category": "accessories",
        "price": 650000,
        "description": "Lơ Kamui Roku cao cấp thế hệ mới, bám bi cực bền, chống trượt cơ hoàn hảo khi ép phê nặng.",
        "desc": "Lơ Kamui Roku cao cấp thế hệ mới, bám bi cực bền, chống trượt cơ hoàn hảo khi ép phê nặng.",
        "img": "images/chalk-kamui-roku.jpg",
        "images": ["images/chalk-kamui-roku.jpg"],
        "specs": {"color": "Sky Blue", "edition": "Roku Hexagonal"},
        "tags": ["kamui", "chalk", "accessory"],
        "stock": 100,
        "is_featured": True
    },
    {
        "name": "Bao Gậy Predator Urbain 2x4",
        "category": "cases",
        "price": 3800000,
        "description": "Bao đựng gậy Predator Urbain 2 gốc 4 ngọn siêu bền bỉ, chống sốc và chống nước chuẩn quốc tế.",
        "desc": "Bao đựng gậy Predator Urbain 2 gốc 4 ngọn siêu bền bỉ, chống sốc và chống nước chuẩn quốc tế.",
        "img": "images/case-predator-urbain.jpg",
        "images": ["images/case-predator-urbain.jpg"],
        "specs": {"capacity": "2 Butts 4 Shafts", "material": "High-density Nylon", "weight": "1.8kg"},
        "tags": ["predator", "case", "urbain"],
        "stock": 15,
        "is_featured": True
    },
    {
        "name": "Bao Cơ JB Custom Rugged 3x6",
        "category": "cases",
        "price": 5200000,
        "description": "Bao đựng cơ JB Cases huyền thoại của Mỹ, khả năng chống rơi đập bảo vệ gậy bida số 1 thế giới.",
        "desc": "Bao đựng cơ JB Cases huyền thoại của Mỹ, khả năng chống rơi đập bảo vệ gậy bida số 1 thế giới.",
        "img": "images/case-jb-custom.jpg",
        "images": ["images/case-jb-custom.jpg"],
        "specs": {"capacity": "3 Butts 6 Shafts", "interior": "Ultra-pad Cushioning"},
        "tags": ["jb", "case"],
        "stock": 8,
        "is_featured": False
    },
    {
        "name": "Đầu Tẩy Predator Victory Soft",
        "category": "accessories",
        "price": 450000,
        "description": "Đầu tẩy 8 lớp da heo tuyển chọn, giữ phom cực lâu, độ đàn hồi và tạo xoáy hàng đầu.",
        "desc": "Đầu tẩy 8 lớp da heo tuyển chọn, giữ phom cực lâu, độ đàn hồi và tạo xoáy hàng đầu.",
        "img": "images/tip-predator-victory.jpg",
        "images": ["images/tip-predator-victory.jpg"],
        "specs": {"diameter": "14mm", "hardness": "Soft", "layers": "8 layers"},
        "tags": ["predator", "tip"],
        "stock": 50,
        "is_featured": False
    },
    {
        "name": "Găng Tay Thi Đấu Predator Second Skin",
        "category": "accessories",
        "price": 650000,
        "description": "Găng tay bida chuyên nghiệp co giãn thoáng khí, vuốt cơ êm ái kể cả khi tay ra nhiều mồ hôi.",
        "desc": "Găng tay bida chuyên nghiệp co giãn thoáng khí, vuốt cơ êm ái kể cả khi tay ra nhiều mồ hôi.",
        "img": "images/glove-predator.jpg",
        "images": ["images/glove-predator.jpg"],
        "specs": {"size": "L/XL", "material": "Breathable Lycra", "hand": "Left hand"},
        "tags": ["predator", "glove"],
        "stock": 40,
        "is_featured": False
    }
]

class UserRole(str, enum.Enum):
    user = 'user'
    admin = 'admin'

metadata_mysql = MetaData()
inventory_table = Table(
    'inventory', metadata_mysql,
    Column('id', Integer, primary_key=True),
    Column('product_id', String(100), unique=True, nullable=False),
    Column('quantity', Integer, default=0),
    Column('reserved', Integer, default=0),
    Column('last_updated', DateTime, default=datetime.utcnow)
)

metadata_pg = MetaData()
users_table = Table(
    'users', metadata_pg,
    Column('id', Integer, primary_key=True),
    Column('username', String(50), unique=True, nullable=False),
    Column('email', String(100), unique=True, nullable=False),
    Column('password_hash', String(255), nullable=False),
    Column('full_name', String(100)),
    Column('phone', String(20)),
    Column('address', Text),
    Column('role', SQLEnum(UserRole), default=UserRole.user),
    Column('created_at', DateTime, default=datetime.utcnow),
    Column('is_active', Integer, default=1)
)

async def seed_data():
    print("Bắt đầu seed data...")
    
    # 1. MongoDB (Catalog)
    mongo_client = AsyncIOMotorClient(MONGO_URL)
    db_mongo = mongo_client['catalog_db']
    
    await db_mongo.products.delete_many({})
    print("Đã xoá dữ liệu cũ trong MongoDB")
    
    # 2. MySQL (Inventory)
    mysql_engine = create_engine(MYSQL_URL)
    metadata_mysql.create_all(bind=mysql_engine)
    
    with mysql_engine.begin() as conn:
        conn.execute(inventory_table.delete())
    print("Đã xoá dữ liệu cũ trong MySQL")
    
    # Redis connection for real-time stock
    REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    try:
        import redis.asyncio as aioredis
        redis_client = aioredis.from_url(REDIS_URL, decode_responses=True)
        await redis_client.ping()
        print("Đã kết nối Redis để đồng bộ tồn kho Real-Time")
    except Exception as e:
        redis_client = None
        print(f"Bỏ qua Redis (không kết nối được: {e})")

    # Insert products and inventory
    for p in products_data:
        stock = p.pop("stock", 0)
        p["created_at"] = datetime.utcnow()
        if not p.get("images"):
            p["images"] = []
        result = await db_mongo.products.insert_one(p)
        product_id_str = str(result.inserted_id)
        
        with mysql_engine.begin() as conn:
            conn.execute(inventory_table.insert().values(
                product_id=product_id_str,
                quantity=stock,
                reserved=0
            ))

        # Đồng bộ vào Redis Real-time Engine
        if redis_client:
            try:
                await redis_client.set(f"stock:{product_id_str}", str(stock))
                await redis_client.set(f"reserved:{product_id_str}", "0")
            except Exception:
                pass
            
    if redis_client:
        await redis_client.close()

    print("Đã seed xong sản phẩm, tồn kho MySQL và Redis Real-time Engine")

    # 3. PostgreSQL (Admin User)
    pg_engine = create_engine(POSTGRES_URL)
    metadata_pg.create_all(bind=pg_engine)
    
    with pg_engine.begin() as conn:
        admin_user = conn.execute(users_table.select().where(users_table.c.username == "admin")).fetchone()
        if not admin_user:
            conn.execute(users_table.insert().values(
                username="admin",
                email="admin@bidacaocap.com",
                password_hash=hash_password("admin123"),
                full_name="Quản Trị Viên",
                role=UserRole.admin
            ))
            print("Đã tạo user admin mặc định (admin/admin123)")
        else:
            print("User admin đã tồn tại")

    print("Seed data hoàn tất!")

if __name__ == "__main__":
    asyncio.run(seed_data())
