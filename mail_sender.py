from db import JerseyDB
import smtplib
from email.mime.text import MIMEText
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

database = JerseyDB()

class EmailSender:
    def __init__(self):
        self.db = database.get_sorted_items()
        self.email_password = os.getenv("EMAIL_PASSWORD")
        self.email = os.getenv("EMAIL")
        self.receiving_emails = [self.email]
        self.available_products = {}

    def to_dict(self, item):
        return {
            "Title": item.title,
            "Price": item.price,
            "Link": item.link,
            "Sale": item.sale,
            "is_new": item.is_new,
            "favourite_team": item.favourite_team
        }

    def get_data(self):
        for db_element in self.db:
            self.available_products[f'Product {self.db.index(db_element)}'] = self.to_dict(db_element)

    def build_email_rows(self, items):
        rows = ""

        for item in items.values():
            rows += f"""
            <tr style="background:{'#f8d7da' if item['favourite_team'] else '#d4edda' if item['Sale'] else '#fff'};">
                <td style="border:1px solid #ddd; padding:8px;">{item['Title']}</td>
                <td style="border:1px solid #ddd; padding:8px;">{item['Price']}</td>
                <td style="border:1px solid #ddd; padding:8px;">{'Sale🔥' if item['Sale'] else 'Regular Price'}</td>
                <td style="border:1px solid #ddd; padding:8px;">{'New' if item['is_new'] else 'Old'}</td>
                <td style="border:1px solid #ddd; padding:8px;"><a href="{item['Link']}">View</a></td>
            </tr>
            """

        return rows

    def send_email(self):
        with open(os.path.join(BASE_DIR, "email_template.html"), "r", encoding="utf-8") as f:
            template = f.read()

        print(self.available_products)
        rows = self.build_email_rows(self.available_products)

        ready_email = template.replace("{{ROWS}}", rows)

        server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
        server.login(self.email, self.email_password)

        for email in self.receiving_emails:
            msg = MIMEText(ready_email, "html")
            msg["Subject"] = f'Signed Football Jerseys - {datetime.now().strftime("%d/%m/%Y")}'
            msg["From"] = self.email
            msg["To"] = email

            server.send_message(msg)

        server.quit()


