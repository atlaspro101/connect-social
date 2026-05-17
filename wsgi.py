from app import app, init_db
import os

# Инициализируем БД при старте
init_db()

if __name__ == "__main__":
    app.run()