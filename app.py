from flask import Flask, request, redirect, url_for, render_template
from dotenv import load_dotenv
import os
from sqlalchemy import create_engine, func
from sqlalchemy.orm import Session

from models.recipe import Base, Recipe
from utils.database import get_database_url

load_dotenv()

DATABASE_URL = get_database_url()
engine = create_engine(DATABASE_URL, pool_pre_ping=True) if DATABASE_URL else None

# 初回のみテーブル作成
if engine:
    Base.metadata.create_all(engine)

app = Flask(__name__)

def _to_bool_env(value, default=False):
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


@app.route("/", methods=["GET", "POST"])
def index():
    errors = []
    form_values = {"title": "", "minutes": "", "description": ""}

    if request.method == "POST":
        title = (request.form.get("title") or "").strip()
        minutes_raw = (request.form.get("minutes") or "").strip()
        description = (request.form.get("description") or "").strip()

        form_values = {
            "title": title,
            "minutes": minutes_raw,
            "description": description,
        }

        # バリデーション
        if not title:
            errors.append("タイトルは必須です。")
        elif len(title) > 200:
            errors.append("タイトルは200文字以内で入力してください。")

        try:
            minutes_val = int(minutes_raw)
            if minutes_val < 1:
                errors.append("所要分数は1以上の整数で入力してください。")
        except ValueError:
            errors.append("所要分数は整数で入力してください。")

        if engine is None:
            errors.append("データベースが未設定です。DATABASE_URL を設定してください。")

        if not errors and engine:
            with Session(engine) as session:
                item = Recipe(
                    title=title,
                    minutes=minutes_val,
                    description=description or None
                )
                session.add(item)
                session.commit()
            return redirect(url_for("index"))

    recipes = []
    if engine:
        with Session(engine) as session:
            recipes = (
                session.query(Recipe)
                .order_by(Recipe.created_at.desc(), Recipe.id.desc())
                .all()
            )

    return render_template(
        "index.html",
        errors=errors,
        recipes=recipes,
        form_values=form_values,
        db_ready=(engine is not None),
        debug=os.getenv("DEBUG", "false"),
        port=os.getenv("PORT", "8000"),
    )


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    debug = _to_bool_env(os.getenv("DEBUG"), default=False)
    app.run(host="0.0.0.0", port=port, debug=debug)
