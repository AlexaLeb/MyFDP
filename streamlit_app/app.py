"""Streamlit UI для сервиса квантильного прогнозирования спроса (MFDP).

Поток: логин → загрузка CSV → опрос статуса задачи → график [q10,q90]+q50,
таблица результатов, скачивание CSV. Авторизация — через REST API (JWT в cookie,
который держит requests.Session в session_state).
"""
import io
import os
import time

import altair as alt
import pandas as pd
import requests
import streamlit as st

API_URL = os.environ.get("API_URL", "http://localhost:8080")
POLL_TIMEOUT_S = 120
POLL_INTERVAL_S = 2
CREDITS_PACK = 150  # размер пакета кредитов за одну «покупку» (оплата fake, MVP)

st.set_page_config(page_title="MFDP — прогноз спроса", page_icon="📈", layout="wide")


def get_session() -> requests.Session:
    if "http" not in st.session_state:
        st.session_state.http = requests.Session()
    return st.session_state.http


def api(method: str, path: str, **kwargs):
    return getattr(get_session(), method)(f"{API_URL}{path}", timeout=30, **kwargs)


# ---------- Аутентификация ----------
def do_login(email: str, password: str) -> bool:
    try:
        r = api("post", "/login/token", data={"username": email, "password": password})
    except requests.RequestException as e:
        st.error(f"Сервис недоступен: {e}")
        return False
    if r.status_code == 200:
        st.session_state.user = email
        return True
    st.error("Неверный email или пароль")
    return False


def do_signup(email: str, password: str) -> bool:
    try:
        r = api("post", "/api/users/signup", json={"email": email, "password": password})
    except requests.RequestException as e:
        st.error(f"Сервис недоступен: {e}")
        return False
    if r.status_code == 201:
        st.success(f"Регистрация успешна, начислено {r.json().get('credits')} кредитов. Войдите.")
        return True
    st.error(r.json().get("detail", "Ошибка регистрации"))
    return False


def get_balance():
    try:
        r = api("get", "/api/balance/")
        if r.status_code == 200:
            return r.json()["balance"]
    except requests.RequestException:
        pass
    return None


# ---------- Сайдбар: вход / регистрация ----------
def auth_sidebar():
    with st.sidebar:
        st.header("Аккаунт")
        if st.session_state.get("user"):
            st.success(f"Вы вошли: {st.session_state.user}")
            bal = get_balance()
            if bal is not None:
                st.metric("Баланс, кредитов", f"{bal:.0f}")
            if st.button("Выйти"):
                api("get", "/login/logout")
                st.session_state.clear()
                st.rerun()
            return

        tab_login, tab_signup = st.tabs(["Вход", "Регистрация"])
        with tab_login:
            email = st.text_input("Email", key="li_email")
            pw = st.text_input("Пароль", type="password", key="li_pw")
            if st.button("Войти"):
                if do_login(email, pw):
                    st.rerun()
        with tab_signup:
            email = st.text_input("Email", key="su_email")
            pw = st.text_input("Пароль", type="password", key="su_pw")
            if st.button("Создать аккаунт"):
                do_signup(email, pw)


# ---------- Прогноз ----------
def run_forecast(file_bytes: bytes, filename: str, horizon: int):
    files = {"file": (filename, file_bytes, "text/csv")}
    r = api("post", "/api/v1/upload", files=files, data={"horizon": str(horizon)})
    if r.status_code == 402:
        st.error("Недостаточно кредитов. Пополните баланс.")
        return None
    if r.status_code == 400:
        st.error(f"Ошибка в данных: {r.json().get('detail')}")
        return None
    if r.status_code != 202:
        st.error(f"Ошибка {r.status_code}: {r.text}")
        return None

    job_id = r.json()["job_id"]
    st.info(f"Задача #{job_id} принята ({r.json()['sku_count']} SKU). Считаем...")

    progress = st.progress(0.0, text="Обработка...")
    waited = 0
    while waited < POLL_TIMEOUT_S:
        time.sleep(POLL_INTERVAL_S)
        waited += POLL_INTERVAL_S
        jr = api("get", f"/api/v1/jobs/{job_id}")
        status = jr.json().get("status")
        progress.progress(min(waited / POLL_TIMEOUT_S, 0.95), text=f"Статус: {status}")
        if status == "done":
            progress.progress(1.0, text="Готово")
            return job_id
        if status == "failed":
            st.error(f"Задача провалена: {jr.json().get('error_message')}")
            return None
    st.warning("Превышено время ожидания.")
    return None


def show_results(job_id: int):
    r = api("get", f"/api/v1/results/{job_id}")
    if r.status_code != 200:
        st.error("Не удалось получить результаты")
        return
    df = pd.DataFrame(r.json()["results"])
    if df.empty:
        st.warning("Пустой результат")
        return
    df["date"] = pd.to_datetime(df["date"])

    skus = sorted(df["sku_id"].unique())
    sku = st.selectbox("SKU", skus)
    sub = df[df["sku_id"] == sku]

    band = (
        alt.Chart(sub)
        .mark_area(opacity=0.3, color="#4c78a8")
        .encode(x="date:T", y=alt.Y("q10:Q", title="Продажи"), y2="q90:Q")
    )
    line = alt.Chart(sub).mark_line(color="#1f3b6f").encode(x="date:T", y="q50:Q")
    st.altair_chart((band + line).properties(height=360), use_container_width=True)
    st.caption("Лента — интервал [q0.1, q0.9], линия — медиана q0.5")

    st.dataframe(df, use_container_width=True, hide_index=True)
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button("Скачать прогноз (CSV)", csv, f"forecast_{job_id}.csv", "text/csv")


# ---------- Покупка кредитов ----------
def credits_page():
    st.subheader("💳 Покупка кредитов")
    bal = get_balance()
    if bal is not None:
        st.metric("Текущий баланс, кредитов", f"{bal:.0f}")
    st.caption(f"Один прогноз стоит 50 кредитов. Пакет — {CREDITS_PACK} кредитов (оплата демо).")

    if st.button(f"Купить кредиты (+{CREDITS_PACK})", type="primary"):
        try:
            r = api("post", "/api/balance/", json={"amount": CREDITS_PACK})
        except requests.RequestException as e:
            st.error(f"Сервис недоступен: {e}")
            return
        if r.status_code == 200:
            st.success(f"Начислено {CREDITS_PACK} кредитов. Новый баланс: {r.json()['balance']:.0f}")
        else:
            st.error(f"Ошибка {r.status_code}: {r.text}")


# ---------- Главный экран ----------
def main():
    st.title("📈 Квантильный прогноз спроса")
    auth_sidebar()

    if not st.session_state.get("user"):
        st.info("Войдите или зарегистрируйтесь в панели слева, чтобы загрузить данные.")
        return

    tab_forecast, tab_credits = st.tabs(["📊 Прогноз", "💳 Кредиты"])

    with tab_forecast:
        st.subheader("Загрузка данных")
        st.caption("CSV с колонками: `date`, `sku_id`, `sales`. Минимум 60 дней истории на SKU.")
        uploaded = st.file_uploader("CSV-файл", type=["csv"])
        horizon = st.selectbox("Горизонт прогноза, дней", [7, 14, 28])

        if uploaded is not None and st.button("Построить прогноз", type="primary"):
            job_id = run_forecast(uploaded.getvalue(), uploaded.name, horizon)
            if job_id:
                st.session_state.last_job = job_id

        if st.session_state.get("last_job"):
            st.divider()
            st.subheader(f"Результаты задачи #{st.session_state.last_job}")
            show_results(st.session_state.last_job)

    with tab_credits:
        credits_page()


if __name__ == "__main__":
    main()
