import os
import asyncio
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from motor.motor_asyncio import AsyncIOMotorClient
from models.order_mysql import Inventory, Base as MyBase
from models.user_postgres import User, Base as PgBase
from core.security import hash_password

MONGO_URL = os.getenv('MONGO_URL', 'mongodb://admin:admin123@mongo-db:27017/')
MYSQL_URL = os.getenv('MYSQL_URL', 'mysql+pymysql://admin:admin123@mysql-db:3306/order_db')
POSTGRES_URL = os.getenv('POSTGRES_URL', 'postgresql://admin:admin123@postgres-db:5432/user_db')

products_data = [
    {
        "name": "Gậy Lỗ Predator SP2 Revo",
        "category": "gay_lo",
        "price": 18500000,
        "description": "Gậy lỗ Predator SP2 Revo với công nghệ ngọn carbon siêu nhẹ và bền, cho độ chính xác tuyệt đối.",
        "specs": {"weight": "19oz", "tip": "Predator Victory (Soft)", "joint": "Uni-Loc"},
        "tags": ["predator", "revo", "carbon"],
        "stock": 10,
        "is_featured": True
    },
    {
        "name": "Gậy Lỗ Mezz EC7",
        "category": "gay_lo",
        "price": 12000000,
        "description": "Mezz EC7 kết hợp vẻ đẹp truyền thống và công nghệ hiện đại. Cân bằng hoàn hảo.",
        "specs": {"weight": "19.5oz", "tip": "Kamui (Medium)", "joint": "United"},
        "tags": ["mezz", "wood"],
        "stock": 5,
        "is_featured": True
    },
    {
        "name": "Gậy Lỗ Lucasi Custom",
        "category": "gay_lo",
        "price": 8500000,
        "description": "Thiết kế tinh xảo, gỗ Maple cao cấp từ Lucasi.",
        "specs": {"weight": "19oz", "tip": "Everest", "joint": "Uni-Loc"},
        "tags": ["lucasi", "custom"],
        "stock": 15,
        "is_featured": False
    },
    {
        "name": "Gậy Lỗ McDermott G-Series",
        "category": "gay_lo",
        "price": 9000000,
        "description": "Gậy McDermott G-Series sản xuất tại Mỹ, độ bền cao.",
        "specs": {"weight": "19oz", "tip": "Navigator Black", "joint": "3/8x10"},
        "tags": ["mcdermott"],
        "stock": 8,
        "is_featured": False
    },
    {
        "name": "Gậy Lỗ Cuetec Cynergy 15K",
        "category": "gay_lo",
        "price": 15000000,
        "description": "Gậy carbon Cuetec Cynergy với công nghệ 15K.",
        "specs": {"weight": "19oz", "tip": "Sniper", "joint": "3/8x14"},
        "tags": ["cuetec", "carbon"],
        "stock": 12,
        "is_featured": True
    },
    {
        "name": "Ngọn Predator Revo 12.4",
        "category": "ngon",
        "price": 11000000,
        "description": "Ngọn Revo 12.4mm bằng carbon, không cong vênh.",
        "specs": {"tip_size": "12.4mm", "material": "Carbon Composite"},
        "tags": ["predator", "shaft", "carbon"],
        "stock": 20,
        "is_featured": True
    },
    {
        "name": "Ngọn Cuetec Cynergy 15K",
        "category": "ngon",
        "price": 9500000,
        "description": "Ngọn Cynergy 15K cho cảm giác đánh thật tay.",
        "specs": {"tip_size": "12.5mm", "material": "Carbon Composite"},
        "tags": ["cuetec", "shaft", "carbon"],
        "stock": 15,
        "is_featured": False
    },
    {
        "name": "Ngọn Predator Z-3 Shaft",
        "category": "ngon",
        "price": 7500000,
        "description": "Ngọn Z-3 gỗ ép công nghệ cao, độ văng thấp.",
        "specs": {"tip_size": "11.85mm", "material": "Wood"},
        "tags": ["predator", "shaft", "wood"],
        "stock": 10,
        "is_featured": False
    },
    {
        "name": "Lơ Kamui (Kamui Chalk)",
        "category": "phu_kien",
        "price": 500000,
        "description": "Lơ Kamui cao cấp, bám bóng cực tốt.",
        "specs": {"color": "Blue", "type": "0.98"},
        "tags": ["kamui", "chalk", "accessory"],
        "stock": 100,
        "is_featured": True
    },
    {
        "name": "Đầu tẩy Predator Victory",
        "category": "phu_kien",
        "price": 600000,
        "description": "Đầu tẩy Predator Victory nhiều lớp.",
        "specs": {"hardness": "Medium", "layers": 8},
        "tags": ["predator", "tip", "accessory"],
        "stock": 50,
        "is_featured": False
    },
    {
        "name": "Cuộn bọc da thật (Leather Wrap)",
        "category": "phu_kien",
        "price": 1200000,
        "description": "Da bọc cán gậy thật cao cấp.",
        "specs": {"material": "Real Leather", "color": "Black"},
        "tags": ["wrap", "leather", "accessory"],
        "stock": 30,
        "is_featured": False
    },
    {
        "name": "Bao Gậy Predator Urbain",
        "category": "bao_gay",
        "price": 3500000,
        "description": "Bao đựng gậy Predator Urbain 2x4 cao cấp.",
        "specs": {"capacity": "2 Butts 4 Shafts", "material": "Nylon"},
        "tags": ["predator", "case"],
        "stock": 15,
        "is_featured": True
    },
    {
        "name": "Bao Gậy JB Cases",
        "category": "bao_gay",
        "price": 4200000,
        "description": "Bao JB Custom 3x6 bảo vệ tuyệt đối.",
        "specs": {"capacity": "3 Butts 6 Shafts", "material": "Leather/Nylon"},
        "tags": ["jb", "case"],
        "stock": 8,
        "is_featured": False
    },
    {
        "name": "Bao Gậy Mezz MZ-35T",
        "category": "bao_gay",
        "price": 2800000,
        "description": "Bao đựng 3 cán 5 ngọn gọn nhẹ của Mezz.",
        "specs": {"capacity": "3 Butts 5 Shafts", "material": "Synthetic"},
        "tags": ["mezz", "case"],
        "stock": 12,
        "is_featured": False
    },
    {
        "name": "Găng tay Predator Second Skin",
        "category": "phu_kien",
        "price": 850000,
        "description": "Găng tay cao cấp, thoáng khí và mượt mà.",
        "specs": {"size": "M, L", "color": "Black/Yellow"},
        "tags": ["predator", "glove", "accessory"],
        "stock": 40,
        "is_featured": False
    }
]

async def seed_data():
    print("Bắt đầu seed data...")
    
    # 1. MongoDB (Catalog)
    mongo_client = AsyncIOMotorClient(MONGO_URL)
    db_mongo = mongo_client['catalog_db']
    
    await db_mongo.products.delete_many({})
    print("Đã xoá dữ liệu cũ trong MongoDB")
    
    # 2. MySQL (Inventory)
    mysql_engine = create_engine(MYSQL_URL)
    MyBase.metadata.create_all(bind=mysql_engine)
    SessionMysql = sessionmaker(bind=mysql_engine)
    mysql_session = SessionMysql()
    
    mysql_session.query(Inventory).delete()
    mysql_session.commit()
    print("Đã xoá dữ liệu cũ trong MySQL")
    
    # Insert products and inventory
    for p in products_data:
        stock = p.pop("stock", 0)
        p["created_at"] = datetime.utcnow()
        p["images"] = []
        result = await db_mongo.products.insert_one(p)
        
        inv = Inventory(
            product_id=str(result.inserted_id),
            quantity=stock,
            reserved=0
        )
        mysql_session.add(inv)
        
    mysql_session.commit()
    mysql_session.close()
    print("Đã seed xong sản phẩm và tồn kho")

    # 3. PostgreSQL (Admin User)
    pg_engine = create_engine(POSTGRES_URL)
    PgBase.metadata.create_all(bind=pg_engine)
    SessionPg = sessionmaker(bind=pg_engine)
    pg_session = SessionPg()

    admin_user = pg_session.query(User).filter(User.username == "admin").first()
    if not admin_user:
        new_admin = User(
            username="admin",
            email="admin@bidacaocap.com",
            password_hash=hash_password("admin123"),
            full_name="Quản Trị Viên",
            role="admin"
        )
        pg_session.add(new_admin)
        pg_session.commit()
        print("Đã tạo user admin mặc định (admin/admin123)")
    else:
        print("User admin đã tồn tại")

    pg_session.close()
    print("Seed data hoàn tất!")

if __name__ == "__main__":
    asyncio.run(seed_data())
