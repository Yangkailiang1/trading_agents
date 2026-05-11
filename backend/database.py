import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)

env_path = os.path.join(PROJECT_ROOT, ".env")
load_dotenv(dotenv_path=env_path)

# SQLite for simplicity, no external DB needed
DB_PATH = os.path.join(BACKEND_DIR, "trading.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False}, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    import models  # noqa: ensure tables registered
    Base.metadata.create_all(bind=engine)
    _migrate()


def _migrate():
    """简易迁移：为现有表添加新列"""
    import sqlalchemy as sa

    with engine.connect() as conn:
        # 检查 positions 表是否已有 buy_date 列
        result = conn.execute(sa.text("PRAGMA table_info(positions)"))
        columns = {row[1] for row in result}
        if 'buy_date' not in columns:
            conn.execute(sa.text("ALTER TABLE positions ADD COLUMN buy_date DATE"))
            conn.commit()
            print("迁移: 已添加 positions.buy_date 列")

        # 检查 trading_decisions 表是否已有 debate_id 列
        result = conn.execute(sa.text("PRAGMA table_info(trading_decisions)"))
        columns = {row[1] for row in result}
        if 'debate_id' not in columns:
            conn.execute(sa.text("ALTER TABLE trading_decisions ADD COLUMN debate_id VARCHAR(50)"))
            conn.commit()
            print("迁移: 已添加 trading_decisions.debate_id 列")

        # 检查 agent_opinions 表是否存在（由 create_all 创建，此处做安全检查）
        result = conn.execute(sa.text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='agent_opinions'"
        ))
        if not result.fetchone():
            conn.execute(sa.text("""
                CREATE TABLE agent_opinions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    debate_id VARCHAR(50) NOT NULL,
                    stock_code VARCHAR(20) NOT NULL,
                    stock_name VARCHAR(100),
                    agent_name VARCHAR(20) NOT NULL,
                    agent_role VARCHAR(50) NOT NULL,
                    action VARCHAR(10) NOT NULL,
                    quantity INTEGER DEFAULT 0,
                    confidence FLOAT DEFAULT 0,
                    reasoning TEXT,
                    is_final BOOLEAN DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.execute(sa.text("CREATE INDEX idx_opinion_debate_id ON agent_opinions(debate_id)"))
            conn.execute(sa.text("CREATE INDEX idx_opinion_stock_code ON agent_opinions(stock_code)"))
            conn.execute(sa.text("CREATE INDEX idx_opinion_created_at ON agent_opinions(created_at)"))
            conn.commit()
            print("迁移: 已创建 agent_opinions 表")
