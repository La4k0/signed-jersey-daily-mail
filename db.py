import os
import re
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, Text, Float, DateTime, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime

load_dotenv()

db_password = os.getenv("DB_PASSWORD")
db_raw_url = os.getenv("DB_POSTGRES_URL")

DATABASE_URL = re.sub(r'_PASSWORD_', db_password, db_raw_url)

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
Base = declarative_base()

class Jersey(Base):
    __tablename__ = "jerseys"

    id = Column(Integer, primary_key=True)
    title = Column(Text)
    price = Column(Text)
    link = Column(Text)
    sale = Column(Boolean)
    favourite_team = Column(Boolean)
    is_new = Column(Boolean)

class JerseyDB:
    def __init__(self):
        self.session = Session()

    def create_tables(self):
        Base.metadata.create_all(engine)

    def save_items(self, items):
        for item in items.values():

            existing = self.session.query(Jersey).filter(
                Jersey.link == item["Link"]
            ).first()

            if existing:
                existing.is_new = False
                existing.favourite_team = item["favourite_team"]
                existing.sale = item.get("Sale", False)
            else:
                row = Jersey(
                    title=item["Title"],
                    price=item["Price"],
                    link=item["Link"],
                    sale=item.get("Sale", False),
                    favourite_team=item["favourite_team"],
                    is_new=True
                )

                self.session.add(row)

        self.session.commit()

    def get_sorted_items(self):
        return (
            self.session.query(Jersey)
            .order_by(
                Jersey.sale.desc(),
                Jersey.is_new.desc()
            )
            .all()
        )

    def close(self):
        self.session.close()