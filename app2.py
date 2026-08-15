import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import math
import requests
import yfinance as yf
import os
import logging
import base64
import re
import html
import secrets as pysecrets
import hashlib
import hmac
from urllib.parse import urlencode
from zoneinfo import ZoneInfo
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
import firebase_admin
from firebase_admin import credentials, firestore, auth
import extra_streamlit_components as stx
import streamlit.components.v1 as components

# --- 1. SAYFA YAPILANDIRMASI ---
st.set_page_config(
    page_title="IZFIN",
    page_icon="💠",
    layout="wide"
)

# --- CSS: Running yazısı gizlenir, MOBİL MENÜ KESİN OLARAK KORUNUR ---
st.markdown("""
<style>
:root {
  --iz-bg:#050b14; --iz-panel:#08131f; --iz-panel2:#0b1826; --iz-line:#153047;
  --iz-cyan:#18e0e8; --iz-blue:#1689ff; --iz-green:#20e69a; --iz-red:#ff5c6c;
  --iz-amber:#f6bd4b; --iz-text:#edf7ff; --iz-muted:#8298ab;
}
html, body, [data-testid="stAppViewContainer"], .stApp {
  background: radial-gradient(circle at 70% 0%, rgba(22,137,255,.08), transparent 27%), #050b14 !important;
  color:var(--iz-text);
}
[data-testid="stMainBlockContainer"] {max-width:1580px!important;padding-top:1rem!important;padding-bottom:3rem!important;}
header[data-testid="stHeader"] {background:rgba(5,11,20,.72)!important;backdrop-filter:blur(16px);border-bottom:1px solid rgba(35,83,119,.22);box-shadow:none!important;}
[data-testid="stStatusWidget"], [data-testid="stToolbarActions"], .stDeployButton, .stAppStatusIndicator {display:none!important;visibility:hidden!important;opacity:0!important;}
[data-testid="collapsedControl"] {display:flex!important;visibility:visible!important;opacity:1!important;z-index:99999!important;}
[data-testid="stSidebar"] {background:linear-gradient(180deg,#05101b 0%,#06111d 56%,#040a12 100%)!important;border-right:1px solid #122b40;}
[data-testid="stSidebar"] > div:first-child {padding-top:.7rem;}
[data-testid="stSidebar"] label, [data-testid="stSidebar"] p {color:#b9c8d5!important;}
[data-testid="stSidebar"] .stButton button {border:1px solid #173b56!important;background:#091827!important;color:#dff9ff!important;border-radius:10px!important;}
[data-testid="stSidebar"] .stButton button[kind="primary"], button[kind="primary"] {background:linear-gradient(105deg,#0d64dd,#10cfd8)!important;color:#fff!important;border:1px solid #23e4ec!important;box-shadow:0 0 24px rgba(13,147,239,.18)!important;}
.stTabs [data-baseweb="tab-list"] {gap:8px;background:#07121e;border:1px solid #123149;border-radius:13px;padding:6px;}
.stTabs [data-baseweb="tab"] {height:42px;background:transparent;border-radius:9px;color:#8ba1b3;padding:0 18px;}
.stTabs [aria-selected="true"] {background:linear-gradient(105deg,rgba(11,91,201,.8),rgba(13,194,207,.35))!important;color:white!important;border:1px solid rgba(31,218,232,.5)!important;}
[data-testid="stExpander"], [data-testid="stDataFrame"], [data-testid="stMetric"] {border-color:#173249!important;}
[data-testid="stDataFrame"] {border-radius:14px;overflow:hidden;}
.stSelectbox > div > div, .stMultiSelect > div > div, .stTextInput > div > div > input {background:#081522!important;border-color:#183951!important;color:#edf7ff!important;}
hr {border-color:#122a3e!important;}
.kpi-card {background:linear-gradient(145deg,rgba(12,29,45,.95),rgba(7,20,32,.95));padding:18px;border-radius:14px;text-align:left;border:1px solid #17384f;box-shadow:inset 0 1px 0 rgba(255,255,255,.025);color:var(--iz-text);}
.kpi-title {font-size:11px;color:#8298ab;text-transform:uppercase;letter-spacing:1.1px;}
.kpi-value {font-size:28px;font-weight:700;color:#f3fbff;margin-top:5px;}
.kpi-highlight-green {color:#25e6a0;} .kpi-highlight-fire {color:#5de5ff;}
.info-box {background:#081522;padding:15px;border-radius:10px;border-left:4px solid #12bfda;margin-bottom:15px;font-size:13px;color:#c8d7e3;line-height:1.6;}
.dataframe {font-size:12px!important;}
.iz-brand {display:flex;align-items:center;gap:12px;padding:5px 1px 14px;}
.iz-brand img {width:48px;height:48px;border-radius:13px;object-fit:cover;box-shadow:0 0 25px rgba(21,206,226,.14);}
.iz-brand-name {font-size:25px;letter-spacing:6px;font-weight:650;color:#f2f8fc;}
.iz-brand-tag {font-size:8px;letter-spacing:2px;color:#7691a7;margin-top:3px;}
.iz-livebar {display:grid;grid-template-columns:repeat(7,minmax(118px,1fr));gap:7px;margin:2px 0 15px;}
.iz-ticker {background:#07131f;border:1px solid #153047;border-radius:11px;padding:9px 11px;min-height:65px;}
.iz-ticker .n {font-size:10px;color:#8da2b4;letter-spacing:.4px;}
.iz-ticker .v {font-size:17px;color:#f2f8fb;margin-top:3px;font-weight:600;}
.iz-up {color:#1ee5a0!important}.iz-down {color:#ff5c6c!important}
.iz-dashboard {display:grid;grid-template-columns:1.58fr .92fr;gap:14px;margin:6px 0 14px;}
.iz-card {background:linear-gradient(145deg,#081522,#07111d);border:1px solid #17354b;border-radius:15px;padding:17px;}
.iz-card-title {font-size:14px;font-weight:650;letter-spacing:.4px;color:#f2f9ff;margin-bottom:11px;}
.iz-pulse {display:grid;grid-template-columns:175px 1fr;gap:20px;align-items:center;}
.iz-gauge {width:145px;height:145px;border-radius:50%;display:grid;place-items:center;background:conic-gradient(#16e1e6 0 var(--pulse),#12416a var(--pulse) 100%);position:relative;box-shadow:0 0 30px rgba(18,191,229,.12);}
.iz-gauge:after {content:"";position:absolute;inset:10px;border-radius:50%;background:#07131f;border:1px solid #173d57;}
.iz-gauge-content {z-index:1;text-align:center}.iz-gauge-num {font-size:38px;font-weight:700}.iz-gauge-label {font-size:11px;color:#1fe4c2;letter-spacing:1px;}
.iz-components {display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-top:13px;}
.iz-comp {background:#091a28;border:1px solid #14364e;border-radius:12px;padding:11px;}
.iz-comp-name {font-size:9px;color:#8ca1b1;letter-spacing:.7px}.iz-comp-val {font-size:21px;font-weight:650;margin-top:4px}.iz-comp-sub {font-size:9px;color:#45d9e6;margin-top:2px;}
.iz-heat-grid {display:grid;grid-template-columns:repeat(4,1fr);gap:5px;}
.iz-heat {border-radius:8px;padding:9px 7px;min-height:62px;border:1px solid rgba(255,255,255,.06);}
.iz-heat strong {display:block;font-size:12px}.iz-heat span {font-size:10px;opacity:.88}
.iz-signals {margin:13px 0;background:#07131f;border:1px solid #17354b;border-radius:15px;padding:16px;}
.iz-signals table {width:100%;border-collapse:collapse;font-size:12px}.iz-signals th {color:#728b9f;text-align:left;font-size:9px;padding:8px;border-bottom:1px solid #17354b;letter-spacing:.5px}.iz-signals td {padding:9px 8px;border-bottom:1px solid rgba(23,53,75,.5);}
.iz-badge {display:inline-block;padding:4px 8px;border-radius:7px;font-size:10px;font-weight:700;border:1px solid;}
.iz-badge.buy {background:rgba(21,210,129,.11);border-color:#1b9c6c;color:#54f0ac}.iz-badge.early {background:rgba(247,184,50,.10);border-color:#946b1d;color:#ffd36d}.iz-badge.wait {background:rgba(38,138,255,.11);border-color:#2167ac;color:#65b7ff}.iz-badge.risk {background:rgba(255,72,85,.10);border-color:#9d3943;color:#ff7782}
.iz-ring {display:inline-grid;place-items:center;width:36px;height:36px;border-radius:50%;background:conic-gradient(#1ee0e5 calc(var(--g)*1%),#17354b 0);position:relative;font-size:9px;font-weight:700}
.iz-ring:after {content:"";position:absolute;inset:4px;background:#07131f;border-radius:50%}.iz-ring span {position:relative;z-index:1}
.iz-hero {padding:6px 2px 12px}.iz-hero h1 {font-size:31px;margin:0;color:#f3f9fc;letter-spacing:-.5px}.iz-hero p {color:#8099ac;margin:5px 0 0;font-size:13px}
.iz-section-label {font-size:10px;color:#1bd7e4;letter-spacing:1.6px;font-weight:650;text-transform:uppercase}
@media(max-width:1100px) {.iz-livebar {grid-template-columns:repeat(3,1fr)}.iz-dashboard {grid-template-columns:1fr}.iz-pulse {grid-template-columns:145px 1fr}}
@media(max-width:700px) {.iz-livebar {grid-template-columns:repeat(2,1fr)}.iz-components {grid-template-columns:repeat(2,1fr)}.iz-heat-grid {grid-template-columns:repeat(2,1fr)}.iz-pulse {grid-template-columns:1fr}.iz-gauge {margin:auto}}

/* --- IZFIN v1.7.1 Signature refinement --- */
[data-testid="stMainBlockContainer"] {max-width:1680px!important;padding-left:1.35rem!important;padding-right:1.35rem!important;}
[data-testid="stSidebar"] {min-width:310px!important;max-width:310px!important;}
[data-testid="stSidebar"] [data-testid="stExpander"] {background:#07131f!important;border:1px solid #17354b!important;border-radius:12px!important;overflow:hidden;}
[data-testid="stSidebar"] [data-testid="stExpander"] details summary {background:#07131f!important;color:#dceaf5!important;}
[data-testid="stSidebar"] [data-testid="stExpander"] details summary:hover {background:#0a1a29!important;}
.iz-brand {padding:12px 3px 18px!important;gap:13px!important;}
.iz-brand img {width:62px!important;height:62px!important;border-radius:16px!important;object-fit:cover!important;object-position:center!important;border:1px solid rgba(35,226,234,.24);box-shadow:0 0 28px rgba(22,196,228,.13)!important;}
.iz-brand-name {font-size:27px!important;letter-spacing:7px!important;}
.iz-brand-tag {font-size:8px!important;color:#68a4c5!important;letter-spacing:2.35px!important;}
.iz-nav-label {font-size:9px;color:#25dce8;letter-spacing:1.7px;font-weight:750;margin:3px 0 8px;text-transform:uppercase;}
.iz-live-shell {display:grid;grid-template-columns:145px 1fr;gap:8px;align-items:stretch;margin:0 0 14px;}
.iz-live-status {background:linear-gradient(145deg,#071522,#081b2b);border:1px solid #17354b;border-radius:12px;padding:10px 12px;display:flex;flex-direction:column;justify-content:center;}
.iz-live-status .s1 {font-size:10px;font-weight:750;color:#e9f8ff;letter-spacing:.6px}.iz-live-status .s2 {font-size:10px;color:#25e6a0;margin-top:3px}.iz-live-status .s3 {font-size:8px;color:#718ba0;margin-top:3px;}
.iz-livebar {margin:0!important;grid-template-columns:repeat(7,minmax(110px,1fr))!important;}
.iz-ticker {border-radius:12px!important;min-height:70px!important;background:linear-gradient(145deg,#071522,#081725)!important;position:relative;overflow:hidden;}
.iz-ticker:after {content:"";position:absolute;left:0;right:0;bottom:0;height:2px;background:linear-gradient(90deg,transparent,#18dce7,transparent);opacity:.28;}
.iz-ticker .v {font-size:18px!important;}
.iz-dashboard {grid-template-columns:1.62fr .98fr!important;gap:14px!important;}
.iz-card {box-shadow:inset 0 1px 0 rgba(255,255,255,.025),0 10px 35px rgba(0,0,0,.13);}
.iz-card-head {display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:12px;}
.iz-card-kicker {font-size:9px;color:#64859b;letter-spacing:.9px;text-transform:uppercase;}
.iz-pulse-copy {font-size:13px;color:#a7bbc9;line-height:1.65;margin-bottom:8px;}
.iz-heat-grid {grid-template-columns:repeat(4,minmax(0,1fr))!important;}
.iz-heat {transition:transform .15s ease,border-color .15s ease;}
.iz-heat:hover {transform:translateY(-2px);border-color:#1db7d1;}
.iz-home-grid {display:grid;grid-template-columns:1.45fr .85fr;gap:14px;margin:13px 0;}
.iz-movers {background:#07131f;border:1px solid #17354b;border-radius:15px;padding:16px;}
.iz-mover-row {display:grid;grid-template-columns:1fr 78px 82px;gap:8px;padding:8px 2px;border-bottom:1px solid rgba(23,53,75,.45);font-size:11px;align-items:center;}
.iz-mover-row:last-child {border-bottom:0}.iz-mover-name {font-weight:700;color:#eaf7ff}.iz-mover-price {color:#9fb3c2;text-align:right}.iz-mover-chg {text-align:right;font-weight:700}
.iz-cta {background:linear-gradient(105deg,rgba(8,58,112,.62),rgba(7,40,73,.72));border:1px solid #145c8e;border-radius:15px;padding:18px;min-height:100%;display:flex;flex-direction:column;justify-content:center;position:relative;overflow:hidden;}
.iz-cta:after {content:"";position:absolute;inset:auto -50px -100px auto;width:220px;height:220px;border-radius:50%;background:radial-gradient(circle,rgba(25,224,232,.18),transparent 66%);}
.iz-cta h3 {margin:0 0 5px;color:#f3fbff;font-size:17px}.iz-cta p {margin:0;color:#8ca7ba;font-size:12px;line-height:1.55}
.iz-scanner-hero {background:linear-gradient(115deg,#081827,#07121e);border:1px solid #17405c;border-radius:16px;padding:18px 20px;margin:4px 0 14px;display:flex;justify-content:space-between;align-items:center;gap:16px;}
.iz-scanner-hero h2 {margin:0;color:#f3fbff;font-size:25px}.iz-scanner-hero p {margin:5px 0 0;color:#829db0;font-size:12px}
.iz-source-note {font-size:9px;color:#638098;margin-top:7px;}
@media(max-width:1200px){.iz-live-shell{grid-template-columns:1fr}.iz-livebar{grid-template-columns:repeat(4,1fr)!important}.iz-home-grid{grid-template-columns:1fr}.iz-dashboard{grid-template-columns:1fr!important}}
@media(max-width:800px){[data-testid="stSidebar"]{min-width:unset!important;max-width:unset!important}.iz-livebar{grid-template-columns:repeat(2,1fr)!important}}

/* --- IZFIN v1.7.2 product polish --- */
[data-testid="stMainBlockContainer"] {padding-top:2.05rem!important;}
[data-testid="stSidebar"] > div:first-child {padding-top:1.35rem!important;}
.iz-brand {align-items:center!important;padding:15px 4px 22px!important;overflow:visible!important;}
.iz-brand img {object-fit:contain!important;object-position:center!important;padding:3px!important;background:#06111d!important;transform:translateY(-2px);overflow:visible!important;}
.iz-brand-copy {display:flex;flex-direction:column;justify-content:center;min-height:62px;}
.iz-quickscan {background:linear-gradient(105deg,rgba(12,98,221,.22),rgba(20,207,216,.12));border:1px solid #1c7399;border-radius:14px;padding:12px 13px;margin:2px 0 14px;color:#dff9ff;}
.iz-quickscan strong {display:block;font-size:12px;color:#f3fbff}.iz-quickscan span{font-size:9px;color:#7da3b9;letter-spacing:.3px}
.iz-home-scan-banner {background:linear-gradient(110deg,rgba(9,57,111,.82),rgba(7,39,70,.88));border:1px solid #147db1;border-radius:15px;padding:15px 18px;margin:13px 0;display:flex;align-items:center;justify-content:space-between;gap:16px;box-shadow:0 0 32px rgba(14,145,209,.08)}
.iz-home-scan-banner .copy strong{font-size:15px;color:#f4fbff}.iz-home-scan-banner .copy span{display:block;color:#8eadc1;font-size:11px;margin-top:3px}
.iz-table-wrap {width:100%;overflow-x:auto;border:1px solid #17354b;border-radius:15px;background:#07131f;margin:10px 0 16px;}
.iz-table {width:100%;border-collapse:separate;border-spacing:0;min-width:1180px;font-size:11px;color:#dcecf7;}
.iz-table thead th {position:sticky;top:0;background:#091725;color:#7092a8;text-align:left;font-size:9px;letter-spacing:.65px;padding:11px 12px;border-bottom:1px solid #1a3c55;white-space:nowrap;z-index:1;}
.iz-table tbody td {padding:11px 12px;border-bottom:1px solid rgba(23,53,75,.58);vertical-align:middle;white-space:nowrap;background:#07131f;}
.iz-table tbody tr:hover td {background:#0a1b2a;}
.iz-table tbody tr:last-child td {border-bottom:0;}
.iz-table .ticker {font-weight:800;color:#f2f9ff}.iz-table .score{font-weight:800;color:#26e2a2}.iz-table .muted{color:#8ca4b6}.iz-table .risk-high{color:#ff7f8b;font-weight:700}.iz-table .risk-mid{color:#ffd06a;font-weight:700}.iz-table .risk-low{color:#55e9b0;font-weight:700}
.iz-auth-bg {position:fixed;inset:0;pointer-events:none;z-index:0;background:radial-gradient(circle at 50% 22%,rgba(13,191,218,.12),transparent 28%),radial-gradient(circle at 15% 85%,rgba(16,111,238,.10),transparent 27%),radial-gradient(circle at 88% 72%,rgba(18,225,217,.06),transparent 23%),linear-gradient(180deg,#030a12 0%,#05101b 55%,#030911 100%);}
.iz-auth-bg:before {content:"";position:absolute;inset:0;opacity:.22;background-image:linear-gradient(rgba(31,119,163,.08) 1px,transparent 1px),linear-gradient(90deg,rgba(31,119,163,.08) 1px,transparent 1px);background-size:46px 46px;mask-image:linear-gradient(to bottom,transparent 0%,black 45%,black 100%);}
.iz-auth-bg:after {content:"";position:absolute;left:8%;right:8%;bottom:4%;height:210px;opacity:.7;background:radial-gradient(ellipse at 50% 100%,rgba(11,174,218,.16),transparent 55%);border-top:1px solid rgba(23,128,173,.09);transform:perspective(480px) rotateX(68deg);}
.iz-auth-shell {position:relative;z-index:1;max-width:590px;margin:3.2vh auto 0;text-align:center;}
.iz-auth-logo {display:flex;align-items:center;justify-content:center;gap:15px;margin-bottom:14px;}
.iz-auth-logo img {width:72px;height:72px;object-fit:contain;border-radius:19px;background:#06131f;border:1px solid rgba(29,225,231,.30);padding:3px;box-shadow:0 0 38px rgba(13,202,225,.13);}
.iz-auth-logo .word {font-size:30px;letter-spacing:8px;color:#f5fbff;font-weight:720;line-height:1;}
.iz-auth-logo .tag {font-size:7.5px;letter-spacing:2.35px;color:#67a8c5;margin-top:7px;text-align:left;}
.iz-auth-kicker {font-size:9px;letter-spacing:2.1px;color:#16dbe4;text-transform:uppercase;font-weight:700;margin-bottom:8px;}
.iz-auth-title {font-size:28px;font-weight:750;color:#f2f9ff;margin:0 0 6px;letter-spacing:-.4px;}
.iz-auth-sub {font-size:11px;color:#7794a8;margin-bottom:18px;}
.iz-auth-card {background:linear-gradient(160deg,rgba(8,23,36,.97),rgba(5,14,24,.98));border:1px solid #17435d;border-radius:20px;padding:14px 17px 8px;box-shadow:0 28px 85px rgba(0,0,0,.36),0 0 44px rgba(12,187,213,.055),inset 0 1px 0 rgba(255,255,255,.025);margin-bottom:-4px;}
.iz-auth-card-head {display:flex;align-items:center;justify-content:space-between;}
.iz-auth-card-head strong {color:#eef9ff;font-size:13px}.iz-auth-card-head span{color:#69899f;font-size:9px;}
.iz-auth-security {display:flex;justify-content:center;gap:18px;margin:15px 0 0;color:#64869b;font-size:9px;flex-wrap:wrap;}
.iz-auth-security b{color:#84b7ca;font-weight:600;}
.iz-google-wrap {margin-top:10px;padding-top:12px;border-top:1px solid rgba(28,65,89,.65);}
.iz-google-caption {font-size:9px;color:#6d8799;text-align:center;margin:0 0 9px;}
.iz-google-note {font-size:8.5px;color:#58758a;text-align:center;margin-top:4px;}
.iz-google-oauth-btn{width:100%;height:46px;border-radius:11px;border:1px solid #cfd9e2;background:linear-gradient(180deg,#fff 0%,#f7fafc 100%);color:#17222d!important;font-size:13px;font-weight:700;text-decoration:none!important;display:flex;align-items:center;justify-content:center;gap:11px;transition:.18s;box-shadow:0 7px 20px rgba(0,0,0,.18),inset 0 1px 0 rgba(255,255,255,.95);}
.iz-google-oauth-btn:hover{transform:translateY(-1px);border-color:#9fb8ca;color:#101c27!important;box-shadow:0 11px 27px rgba(0,0,0,.24);}
.iz-google-g{width:19px;height:19px;display:block;flex:0 0 19px;}
.iz-auth-footer {font-size:8.5px;color:#526e82;margin-top:13px;letter-spacing:.15px;}
[data-testid="stTextInput"] input {border-radius:11px!important;min-height:44px!important;background:#071522!important;border:1px solid #21435a!important;color:#eef8ff!important;box-shadow:inset 0 1px 0 rgba(255,255,255,.02)!important;}
[data-testid="stTextInput"] input:focus {border-color:#17dce5!important;box-shadow:0 0 0 1px rgba(23,220,229,.45),0 0 22px rgba(18,185,221,.10)!important;}
[data-testid="stCheckbox"] label p {font-size:10px!important;color:#bad0df!important;}
[data-testid="stCheckbox"] input {accent-color:#16dbe4!important;}
/* AUTH: Giriş / Kayıt sekmeleri IZFIN segmented switch */
.stTabs [data-baseweb="tab-list"] {gap:6px!important;background:#06131f!important;border:1px solid #173a51!important;border-radius:13px!important;padding:5px!important;margin:8px 0 18px!important;box-shadow:inset 0 1px 0 rgba(255,255,255,.025)!important;}
.stTabs [data-baseweb="tab"] {flex:1!important;justify-content:center!important;min-height:42px!important;border-radius:9px!important;color:#7897aa!important;font-weight:650!important;background:transparent!important;border:1px solid transparent!important;}
.stTabs [data-baseweb="tab"] p {font-size:12px!important;font-weight:700!important;}
.stTabs [data-baseweb="tab"][aria-selected="true"] {color:#f4fcff!important;background:linear-gradient(105deg,rgba(13,101,221,.92),rgba(15,202,214,.70))!important;border:1px solid rgba(37,227,235,.62)!important;box-shadow:0 8px 24px rgba(10,139,220,.15),inset 0 1px 0 rgba(255,255,255,.08)!important;}
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] {display:none!important;}
/* Streamlit primary submit rengini auth markasına sabitle */
[data-testid="stFormSubmitButton"] button, [data-testid="stForm"] button[kind="primary"], button[data-testid="stBaseButton-primary"] {min-height:46px!important;border-radius:11px!important;background:linear-gradient(100deg,#0d72e8 0%,#13cbd7 100%)!important;color:#fff!important;border:1px solid #25dfe8!important;font-weight:750!important;box-shadow:0 10px 28px rgba(11,139,224,.18),inset 0 1px 0 rgba(255,255,255,.12)!important;}
[data-testid="stFormSubmitButton"] button:hover, [data-testid="stForm"] button[kind="primary"]:hover, button[data-testid="stBaseButton-primary"]:hover {transform:translateY(-1px)!important;filter:brightness(1.06)!important;box-shadow:0 13px 32px rgba(12,164,224,.25)!important;}
.iz-google-wrap {position:relative;margin-top:13px;padding-top:18px;border-top:1px solid rgba(32,73,99,.62);}
.iz-google-caption {display:inline-block;position:relative;top:-26px;background:#050f1a;padding:0 10px;font-size:9px;color:#7895a8;text-align:center;margin-bottom:-16px;}
.iz-google-note {font-size:8.5px;color:#58758a;text-align:center;margin-top:4px;}
@media(max-width:850px){.iz-auth-shell{max-width:94%;margin-top:2vh}.iz-auth-logo img{width:62px;height:62px}.iz-auth-logo .word{font-size:25px}.iz-home-scan-banner{flex-direction:column;align-items:flex-start}}

/* v1.7.5 AUTH SWITCH: auth ekranında Streamlit tabs kullanılmaz. */
.iz-auth-switch-label{font-size:9px;color:#66889d;letter-spacing:.9px;text-align:center;margin:4px 0 7px;text-transform:uppercase;}
[data-baseweb="tab-highlight"], [data-baseweb="tab-border"], [role="tab"]::before, [role="tab"]::after, [role="tablist"]::before, [role="tablist"]::after {display:none!important;background:transparent!important;border:0!important;box-shadow:none!important;height:0!important;}
[data-testid="stHorizontalBlock"] [data-testid="stButton"] button {transition:all .18s ease;}

/* v1.7.9 — Native Google OAuth link button */
.st-key-google_oauth_native [data-testid="stLinkButton"] a,
.st-key-google_oauth_native a[data-testid="stBaseLinkButton-secondary"],
.st-key-google_oauth_native a {
    min-height:48px!important;
    width:100%!important;
    border-radius:12px!important;
    background:linear-gradient(180deg,#ffffff 0%,#f5f8fb 100%)!important;
    color:#17222d!important;
    border:1px solid #cfd9e2!important;
    font-weight:760!important;
    font-size:14px!important;
    display:flex!important;
    align-items:center!important;
    justify-content:center!important;
    text-decoration:none!important;
    box-shadow:0 7px 20px rgba(0,0,0,.18),inset 0 1px 0 rgba(255,255,255,.95)!important;
    transition:all .18s ease!important;
}
.st-key-google_oauth_native [data-testid="stLinkButton"] a:hover,
.st-key-google_oauth_native a:hover {
    transform:translateY(-1px)!important;
    border-color:#87d9e2!important;
    box-shadow:0 11px 28px rgba(0,0,0,.24),0 0 0 1px rgba(22,219,228,.10)!important;
}
.st-key-google_oauth_native p {
    color:#17222d!important;
    font-weight:760!important;
}

.st-key-google_oauth_native [data-testid="stLinkButton"] a::before,
.st-key-google_oauth_native a[data-testid="stBaseLinkButton-secondary"]::before {
    content:""!important;
    display:inline-block!important;
    width:19px!important;
    height:19px!important;
    flex:0 0 19px!important;
    margin-right:10px!important;
    background-repeat:no-repeat!important;
    background-position:center!important;
    background-size:19px 19px!important;
    background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 18 18'%3E%3Cpath fill='%234285F4' d='M17.64 9.205c0-.638-.057-1.252-.164-1.841H9v3.482h4.844a4.14 4.14 0 0 1-1.797 2.715v2.258h2.909c1.702-1.567 2.684-3.875 2.684-6.614z'/%3E%3Cpath fill='%2334A853' d='M9 18c2.43 0 4.467-.806 5.956-2.181l-2.909-2.258c-.806.54-1.835.859-3.047.859-2.344 0-4.328-1.585-5.037-3.714H.956v2.332A9 9 0 0 0 9 18z'/%3E%3Cpath fill='%23FBBC05' d='M3.963 10.706A5.41 5.41 0 0 1 3.682 9c0-.592.102-1.167.281-1.706V4.962H.956A9 9 0 0 0 0 9c0 1.452.347 2.827.956 4.038l3.007-2.332z'/%3E%3Cpath fill='%23EA4335' d='M9 3.58c1.321 0 2.507.454 3.44 1.345l2.581-2.582C13.463.891 11.426 0 9 0A9 9 0 0 0 .956 4.962l3.007 2.332C4.672 5.165 6.656 3.58 9 3.58z'/%3E%3C/svg%3E")!important;
}

/* v1.7.6: Auth switch pasif butonunu IZFIN temasına sabitle. */
.st-key-auth_switch_login button,
.st-key-auth_switch_register button {
    min-height:48px!important;
    border-radius:12px!important;
    font-weight:750!important;
    font-size:14px!important;
    background:#081927!important;
    color:#9fc3d6!important;
    border:1px solid #1b4a66!important;
    box-shadow:inset 0 1px 0 rgba(255,255,255,.025)!important;
}
.st-key-auth_switch_login button:hover,
.st-key-auth_switch_register button:hover {
    color:#effcff!important;
    border-color:#1fcbd8!important;
    background:#0a2030!important;
}
.st-key-auth_switch_login button[kind="primary"],
.st-key-auth_switch_register button[kind="primary"],
.st-key-auth_switch_login button[data-testid="stBaseButton-primary"],
.st-key-auth_switch_register button[data-testid="stBaseButton-primary"] {
    background:linear-gradient(105deg,#1378ed 0%,#18cbd3 100%)!important;
    color:#fff!important;
    border:1px solid #28e0e7!important;
    box-shadow:0 9px 25px rgba(12,153,221,.20),inset 0 1px 0 rgba(255,255,255,.10)!important;
}
.st-key-auth_switch_login button p,
.st-key-auth_switch_register button p {color:inherit!important;font-weight:750!important;}



/* v1.7.11 — Google ikonu yazının hemen yanında, birlikte merkezde */
.st-key-google_oauth_native [data-testid="stLinkButton"] a,
.st-key-google_oauth_native a[data-testid="stBaseLinkButton-secondary"] {
    gap:0!important;
    justify-content:center!important;
}
.st-key-google_oauth_native [data-testid="stLinkButton"] a::before,
.st-key-google_oauth_native a[data-testid="stBaseLinkButton-secondary"]::before {
    margin-left:0!important;
    margin-right:9px!important;
    position:static!important;
    transform:none!important;
}


/* v1.7.12 — Google ikonunu metnin hemen soluna sabitle */
.st-key-google_oauth_native [data-testid="stLinkButton"] a,
.st-key-google_oauth_native a[data-testid="stBaseLinkButton-secondary"] {
    position:relative!important;
    justify-content:center!important;
    padding-left:42px!important;
    padding-right:42px!important;
}

.st-key-google_oauth_native [data-testid="stLinkButton"] a::before,
.st-key-google_oauth_native a[data-testid="stBaseLinkButton-secondary"]::before {
    position:absolute!important;
    left:50%!important;
    top:50%!important;
    transform:translate(-122px,-50%)!important;
    margin:0!important;
    width:19px!important;
    height:19px!important;
    flex:none!important;
}

.st-key-google_oauth_native [data-testid="stLinkButton"] a p,
.st-key-google_oauth_native a[data-testid="stBaseLinkButton-secondary"] p {
    margin:0!important;
    padding:0!important;
    text-align:center!important;
}


/* v1.7.14 — Akıllı Tarama ana çalışma alanı */
.iz-scan-control-head{
    margin:18px 0 12px;
    padding:17px 19px;
    display:flex;
    justify-content:space-between;
    align-items:center;
    gap:18px;
    background:linear-gradient(135deg,rgba(7,24,38,.96),rgba(8,31,47,.91));
    border:1px solid #17445f;
    border-radius:16px;
    box-shadow:inset 0 1px 0 rgba(255,255,255,.025),0 15px 38px rgba(0,0,0,.16);
}
.iz-scan-control-head h3{margin:3px 0 3px;color:#f1f9ff;font-size:19px}
.iz-scan-control-head p{margin:0;color:#7899ad;font-size:11px}
.iz-scan-count{
    white-space:nowrap;
    font-size:9px;
    letter-spacing:1px;
    font-weight:750;
    color:#13d8e2;
    border:1px solid #1b566f;
    background:#071927;
    border-radius:999px;
    padding:8px 11px;
}
.iz-scan-selection-summary{
    margin:8px 0 12px;
    padding:12px 14px;
    background:#071724;
    border:1px solid #173e55;
    border-radius:11px;
    color:#91afc0;
    font-size:11px;
}
.iz-scan-selection-summary b{
    color:#19dce4;
    font-size:17px;
    margin-right:4px;
}
@media(max-width:850px){
    .iz-scan-control-head{flex-direction:column;align-items:flex-start}
}


/* v1.7.15 — Canlı hisse autocomplete sonucu */
.iz-search-result-preview{
    display:flex;
    align-items:center;
    justify-content:space-between;
    gap:14px;
    margin:7px 0 10px;
    padding:11px 13px;
    border:1px solid #17445f;
    border-radius:11px;
    background:linear-gradient(135deg,#071724,#092033);
}
.iz-search-result-preview div{
    display:flex;
    align-items:baseline;
    gap:9px;
    min-width:0;
}
.iz-search-result-preview b{
    color:#19dce4;
    font-size:13px;
}
.iz-search-result-preview span{
    color:#d7e7f0;
    font-size:11px;
    overflow:hidden;
    text-overflow:ellipsis;
    white-space:nowrap;
}
.iz-search-result-preview small{
    color:#668da4;
    font-size:9px;
    white-space:nowrap;
}


/* v1.7.16 — Scanner UI polish: beyaz yüzeyleri kaldır, IZFIN dark-glass dili */
.iz-panel-title{
    display:flex;
    align-items:center;
    gap:11px;
    margin:2px 0 14px;
    padding:0 2px;
}
.iz-panel-icon{
    width:30px;
    height:30px;
    display:inline-flex;
    align-items:center;
    justify-content:center;
    border-radius:9px;
    border:1px solid #176078;
    background:linear-gradient(145deg,#082336,#0b3042);
    color:#19dce4;
    font-size:18px;
    box-shadow:inset 0 1px 0 rgba(255,255,255,.04);
}
.iz-panel-title div{display:flex;flex-direction:column;gap:1px}
.iz-panel-title b{font-size:17px;color:#eef8fc;letter-spacing:-.2px}
.iz-panel-title small{font-size:9px;color:#64869a;letter-spacing:.25px}

/* Kişisel liste expander'ını beyaz Streamlit yüzeyinden çıkar */
[data-testid="stExpander"]{
    background:linear-gradient(145deg,rgba(7,22,34,.98),rgba(7,28,42,.94))!important;
    border:1px solid #173f55!important;
    border-radius:13px!important;
    overflow:hidden!important;
    box-shadow:inset 0 1px 0 rgba(255,255,255,.025)!important;
}
[data-testid="stExpander"] details,
[data-testid="stExpander"] summary{
    background:transparent!important;
}
[data-testid="stExpander"] summary{
    min-height:46px!important;
    color:#dcecf4!important;
}
[data-testid="stExpander"] summary:hover{
    background:rgba(17,62,82,.22)!important;
}
[data-testid="stExpander"] summary p{
    color:#dcecf4!important;
    font-weight:650!important;
    font-size:12px!important;
}
[data-testid="stExpander"] svg{
    fill:#18cbd7!important;
    color:#18cbd7!important;
}

/* Disabled kayıtlı liste de beyaz/gri görünmesin */
[data-testid="stMultiSelect"] [data-baseweb="select"] > div{
    background:#071724!important;
    border-color:#1a455c!important;
}
[data-testid="stMultiSelect"] span[data-baseweb="tag"]{
    background:#0d2a3c!important;
    border:1px solid #194e67!important;
    color:#b9d7e5!important;
}
[data-testid="stMultiSelect"] span[data-baseweb="tag"] span{
    color:#b9d7e5!important;
}

/* Secondary butonlar: beyaz blok yerine koyu IZFIN butonu */
button[kind="secondary"],
[data-testid="stBaseButton-secondary"]{
    background:linear-gradient(135deg,#092033,#0a2a3d)!important;
    color:#d9edf5!important;
    border:1px solid #1b536d!important;
    box-shadow:none!important;
}
button[kind="secondary"]:hover,
[data-testid="stBaseButton-secondary"]:hover{
    border-color:#19cbd7!important;
    color:#ffffff!important;
    background:linear-gradient(135deg,#0b2b40,#0c3549)!important;
}

/* Ana scanner CTA */
button[kind="primary"],
[data-testid="stBaseButton-primary"]{
    border:1px solid rgba(29,220,229,.68)!important;
    box-shadow:0 8px 24px rgba(0,173,207,.12)!important;
}

/* Form label ve yardımcı metin kontrastı */
[data-testid="stWidgetLabel"] p{
    color:#7899ad!important;
}


/* v1.7.17 — Hisse ara butonu */
.st-key-stock_search_button button{
    min-height:44px!important;
    margin-top:0!important;
    border-radius:11px!important;
    background:linear-gradient(135deg,#0b2a3e,#0c364a)!important;
    color:#dff8fb!important;
    border:1px solid #1a6078!important;
    font-weight:760!important;
    box-shadow:inset 0 1px 0 rgba(255,255,255,.03)!important;
}
.st-key-stock_search_button button:hover{
    border-color:#19dce4!important;
    background:linear-gradient(135deg,#0d344a,#0e4055)!important;
    color:#ffffff!important;
    box-shadow:0 7px 18px rgba(11,172,204,.12)!important;
}


/* v1.7.18 — Multiselect/tag görünümü: IZFIN dark + cyan */
[data-testid="stMultiSelect"] [data-baseweb="select"] > div {
    background:#071724!important;
    border:1px solid #1a455c!important;
    border-radius:11px!important;
    box-shadow:inset 0 1px 0 rgba(255,255,255,.02)!important;
}

/* Seçili varlık chip'leri: kırmızı Streamlit varsayılanını tamamen kaldır */
[data-testid="stMultiSelect"] span[data-baseweb="tag"],
[data-testid="stMultiSelect"] [data-baseweb="tag"] {
    background:linear-gradient(135deg,#0b2b3d,#0d3a4c)!important;
    border:1px solid #17637a!important;
    border-radius:8px!important;
    color:#dff7fb!important;
    box-shadow:inset 0 1px 0 rgba(255,255,255,.025)!important;
    opacity:1!important;
}

[data-testid="stMultiSelect"] span[data-baseweb="tag"] *,
[data-testid="stMultiSelect"] [data-baseweb="tag"] * {
    color:#dff7fb!important;
    fill:#8fdce5!important;
    opacity:1!important;
}

/* Chip içindeki X ikonu */
[data-testid="stMultiSelect"] [data-baseweb="tag"] button,
[data-testid="stMultiSelect"] [data-baseweb="tag"] svg {
    color:#8fdce5!important;
    fill:#8fdce5!important;
    opacity:.95!important;
}

[data-testid="stMultiSelect"] [data-baseweb="tag"]:hover {
    background:linear-gradient(135deg,#0d3448,#105065)!important;
    border-color:#20d3dc!important;
}

/* Sol taraftaki disabled kişisel listeyi silik göstermesin */
[data-testid="stMultiSelect"] [aria-disabled="true"],
[data-testid="stMultiSelect"] [data-baseweb="select"][aria-disabled="true"],
[data-testid="stMultiSelect"] [data-baseweb="select"] [aria-disabled="true"] {
    opacity:1!important;
    filter:none!important;
}

[data-testid="stMultiSelect"] [aria-disabled="true"] [data-baseweb="tag"],
[data-testid="stMultiSelect"] [data-baseweb="select"][aria-disabled="true"] [data-baseweb="tag"] {
    opacity:1!important;
    background:#0b2637!important;
    border:1px solid #194f66!important;
    color:#bcdce8!important;
}

[data-testid="stMultiSelect"] [aria-disabled="true"] [data-baseweb="tag"] *,
[data-testid="stMultiSelect"] [data-baseweb="select"][aria-disabled="true"] [data-baseweb="tag"] * {
    color:#bcdce8!important;
    opacity:1!important;
}

/* Placeholder ve normal metin kontrastı */
[data-testid="stMultiSelect"] input,
[data-testid="stMultiSelect"] input::placeholder {
    color:#8aaabd!important;
    opacity:1!important;
}


/* v1.7.19 — Streamlit tag stilinden bağımsız IZFIN liste tasarımı */
.iz-saved-list-label{
    margin:8px 0 7px;
    color:#78a8be;
    font-size:11px;
}
.iz-static-chip-wrap{
    display:flex;
    flex-wrap:wrap;
    gap:7px;
}
.iz-saved-list-box{
    padding:12px;
    min-height:48px;
    border:1px solid #17465d;
    border-radius:11px;
    background:#071724;
}
.iz-static-chip{
    display:inline-flex;
    align-items:center;
    padding:6px 9px;
    border-radius:7px;
    border:1px solid #1a5c72;
    background:linear-gradient(135deg,#0b293a,#0d3949);
    color:#d9f3f7!important;
    font-size:11px;
    line-height:1;
    font-weight:650;
    letter-spacing:.15px;
    box-shadow:inset 0 1px 0 rgba(255,255,255,.025);
}
.iz-active-universe{
    margin:7px 0 10px;
    padding:14px;
    border:1px solid #19516a;
    border-radius:12px;
    background:linear-gradient(145deg,#071925,#09283a);
}
.iz-active-universe-top{
    display:flex;
    align-items:center;
    justify-content:space-between;
    gap:12px;
    margin-bottom:11px;
}
.iz-active-universe-top div{
    display:flex;
    flex-direction:column;
    gap:2px;
}
.iz-active-universe-top small{
    color:#5f899e;
    font-size:8px;
    letter-spacing:1px;
    font-weight:750;
}
.iz-active-universe-top strong{
    color:#effaff;
    font-size:14px;
}
.iz-active-universe-top > span{
    color:#18d5df;
    font-size:9px;
    font-weight:800;
    letter-spacing:.7px;
    border:1px solid #1b6077;
    background:#082333;
    border-radius:999px;
    padding:6px 9px;
}
.iz-empty-list{
    color:#66899a;
    font-size:10px;
}


/* v1.7.21 — Projection & Scenario standalone workspace */
.iz-proj-hero{
    display:flex;
    justify-content:space-between;
    align-items:center;
    gap:20px;
    padding:22px 24px;
    margin:0 0 18px;
    border:1px solid #17445f;
    border-radius:17px;
    background:linear-gradient(135deg,#071826,#09283a);
    box-shadow:0 18px 44px rgba(0,0,0,.18),inset 0 1px 0 rgba(255,255,255,.025);
}
.iz-proj-hero h2{margin:4px 0 5px;color:#f3fbff;font-size:25px}
.iz-proj-hero p{margin:0;color:#7595a8;font-size:11px;max-width:760px}
.iz-proj-empty{
    padding:28px;
    border:1px dashed #23536b;
    border-radius:15px;
    background:#071724;
    display:flex;
    flex-direction:column;
    align-items:center;
    gap:6px;
    text-align:center;
}
.iz-proj-empty b{color:#edf9fd;font-size:15px}
.iz-proj-empty span{color:#6f91a5;font-size:10px}
.iz-proj-model-note{
    min-height:73px;
    padding:12px 14px;
    border:1px solid #17445f;
    border-radius:12px;
    background:#071724;
    display:flex;
    flex-direction:column;
    justify-content:center;
}
.iz-proj-model-note small{font-size:8px;letter-spacing:1px;color:#13d8e2}
.iz-proj-model-note b{color:#eaf8fd;font-size:12px;margin:2px 0}
.iz-proj-model-note span{color:#66899d;font-size:9px}
.iz-proj-section-title{
    margin:20px 0 10px;
    font-size:10px;
    font-weight:800;
    letter-spacing:1.25px;
    color:#5fa9c6;
    text-transform:uppercase;
}
.iz-scenario-card{
    min-height:294px;
    padding:18px;
    border-radius:15px;
    background:linear-gradient(145deg,#071724,#092333);
    border:1px solid #17445f;
    box-shadow:inset 0 1px 0 rgba(255,255,255,.025);
}
.iz-scenario-up{border-color:#176456}
.iz-scenario-down{border-color:#6a3342}
.iz-scenario-head{
    display:flex;
    align-items:center;
    gap:10px;
    margin-bottom:16px;
}
.iz-scenario-dot{
    width:11px;height:11px;border-radius:50%;
    box-shadow:0 0 15px currentColor;
}
.iz-scenario-up .iz-scenario-dot{background:#31d59a;color:#31d59a}
.iz-scenario-down .iz-scenario-dot{background:#ff6177;color:#ff6177}
.iz-scenario-head small{
    display:block;font-size:8px;letter-spacing:1px;color:#6f91a5;margin-bottom:2px
}
.iz-scenario-head h3{margin:0;color:#f3fbff;font-size:17px}
.iz-scenario-row{
    display:flex;
    flex-direction:column;
    gap:4px;
    padding:11px 0;
    border-top:1px solid rgba(35,77,99,.58);
}
.iz-scenario-row span{color:#6e91a5;font-size:9px;text-transform:uppercase;letter-spacing:.55px}
.iz-scenario-row b{color:#dceef5;font-size:11px;line-height:1.55;font-weight:650}
.iz-direction-card{
    margin-top:18px;
    padding:17px 19px;
    border-radius:14px;
    background:#071724;
    border:1px solid #20465a;
    display:grid;
    grid-template-columns:220px 1fr;
    gap:18px;
    align-items:center;
}
.iz-direction-card small{font-size:8px;letter-spacing:1px;color:#678da1}
.iz-direction-card h3{margin:3px 0 0;color:#f1f9fd;font-size:17px}
.iz-direction-card p{margin:0;color:#bcd4df;font-size:11px;line-height:1.65}
.iz-direction-up{border-color:#176456;background:linear-gradient(135deg,#071b24,#092a2c)}
.iz-direction-down{border-color:#6a3342;background:linear-gradient(135deg,#1b1118,#21141c)}
.iz-direction-neutral{border-color:#28556c}
@media(max-width:850px){
    .iz-proj-hero{flex-direction:column;align-items:flex-start}
    .iz-direction-card{grid-template-columns:1fr}
}


/* v1.7.23 — Projection readability / contrast pass */

/* Metric kartları: koyu temada silik gri görünümü kaldır */
[data-testid="stMetric"]{
    background:linear-gradient(145deg,rgba(7,23,36,.82),rgba(8,30,45,.72))!important;
    border:1px solid rgba(31,78,101,.72)!important;
    border-radius:12px!important;
    padding:12px 14px!important;
    box-shadow:inset 0 1px 0 rgba(255,255,255,.025)!important;
}

[data-testid="stMetricLabel"]{
    color:#78a8bd!important;
    opacity:1!important;
}
[data-testid="stMetricLabel"] p{
    color:#78a8bd!important;
    font-size:11px!important;
    font-weight:650!important;
    opacity:1!important;
}

[data-testid="stMetricValue"]{
    color:#f1f9fd!important;
    opacity:1!important;
}
[data-testid="stMetricValue"] > div,
[data-testid="stMetricValue"] p{
    color:#f1f9fd!important;
    font-size:30px!important;
    font-weight:730!important;
    letter-spacing:-.5px!important;
    opacity:1!important;
}

[data-testid="stMetricDelta"]{
    opacity:1!important;
}
[data-testid="stMetricDelta"] > div,
[data-testid="stMetricDelta"] p{
    font-size:10px!important;
    font-weight:700!important;
    opacity:1!important;
}

/* Progress alanını daha sofistike ve okunur yap */
[data-testid="stProgress"] > div > div{
    background:#0b2637!important;
    border-radius:999px!important;
    overflow:hidden!important;
}
[data-testid="stProgress"] > div > div > div{
    background:linear-gradient(90deg,#1479ed,#16c9d5)!important;
    border-radius:999px!important;
}

/* Projection sayfasındaki caption / yardımcı metinleri belirginleştir */
.iz-proj-hero p,
.iz-proj-model-note span,
.iz-proj-empty span{
    color:#88a8b9!important;
}

.iz-proj-section-title{
    color:#45c4d6!important;
    font-size:10px!important;
    font-weight:850!important;
    letter-spacing:1.45px!important;
}

/* Teknik senaryo kartlarını daha tok ve okunur yap */
.iz-scenario-card{
    background:linear-gradient(145deg,#081b29,#0a2637)!important;
    box-shadow:
        inset 0 1px 0 rgba(255,255,255,.035),
        0 15px 34px rgba(0,0,0,.15)!important;
}

.iz-scenario-up{
    border-color:#1c7b65!important;
}
.iz-scenario-down{
    border-color:#8a3d50!important;
}

.iz-scenario-head small{
    color:#6fa9bf!important;
    font-size:8.5px!important;
    font-weight:800!important;
    letter-spacing:1.15px!important;
}
.iz-scenario-head h3{
    color:#f6fbfe!important;
    font-size:18px!important;
    font-weight:760!important;
    letter-spacing:-.2px!important;
}

.iz-scenario-row{
    padding:13px 0!important;
    border-top:1px solid rgba(50,96,117,.52)!important;
}
.iz-scenario-row span{
    color:#72a7bd!important;
    font-size:9px!important;
    font-weight:800!important;
    letter-spacing:.75px!important;
}
.iz-scenario-row b{
    color:#edf7fb!important;
    font-size:12px!important;
    line-height:1.6!important;
    font-weight:700!important;
}

/* Algoritmik yön özeti */
.iz-direction-card{
    box-shadow:inset 0 1px 0 rgba(255,255,255,.025)!important;
}
.iz-direction-card small{
    color:#6fa4b9!important;
    font-weight:800!important;
}
.iz-direction-card h3{
    color:#f5fbfe!important;
    font-size:18px!important;
    font-weight:760!important;
}
.iz-direction-card p{
    color:#d2e4ec!important;
    font-size:12px!important;
    line-height:1.72!important;
}
.iz-direction-card p b{
    color:#ffffff!important;
}

/* Genel Projection sayfası yardımcı metin kontrastı */
[data-testid="stCaptionContainer"] p{
    color:#96afbc!important;
    opacity:1!important;
    font-size:10.5px!important;
}

/* Selectbox ve label kontrastı */
[data-testid="stSelectbox"] label p{
    color:#87aabd!important;
    font-weight:650!important;
}


/* v1.7.26 — Tarama tablosu geniş görünüm / focus mode */
.iz-scan-table-wrap{
    position:relative;
    width:100%;
    overflow-x:auto;
    border-radius:14px;
}
.iz-focus-title{
    display:flex;
    align-items:center;
    min-height:62px;
}
.iz-focus-title small{
    display:block;
    color:#22d8e2;
    font-size:8px;
    font-weight:850;
    letter-spacing:1.4px;
    margin-bottom:3px;
}
.iz-focus-title h2{
    margin:0;
    color:#f2faff;
    font-size:23px;
    line-height:1.1;
}
.iz-focus-title p{
    margin:5px 0 0;
    color:#7898aa;
    font-size:10px;
}
.iz-focus-meta{
    display:flex;
    align-items:center;
    gap:8px;
    margin:6px 0 12px;
}
.iz-focus-meta span{
    display:inline-flex;
    padding:6px 9px;
    border-radius:999px;
    border:1px solid #1b5068;
    background:#071a28;
    color:#8fb7ca;
    font-size:9px;
    font-weight:700;
    letter-spacing:.25px;
}
.st-key-scan_table_focus_open button,
.st-key-scan_table_focus_exit button{
    min-height:40px!important;
    border-radius:10px!important;
    background:linear-gradient(135deg,#092338,#0a3448)!important;
    color:#dff8fb!important;
    border:1px solid #1a617a!important;
    font-weight:760!important;
}
.st-key-scan_table_focus_open button:hover,
.st-key-scan_table_focus_exit button:hover{
    border-color:#20d8e1!important;
    background:linear-gradient(135deg,#0b3046,#0d4256)!important;
    color:#fff!important;
}


/* v1.7.27 — Kapanmış Pozisyon Geçmişi: IZFIN native table */
.iz-closed-kpis{
    display:grid;
    grid-template-columns:repeat(4,minmax(0,1fr));
    gap:9px;
    margin:4px 0 12px;
}
.iz-closed-kpis>div{
    padding:11px 12px;
    border:1px solid #17445d;
    border-radius:11px;
    background:linear-gradient(145deg,#071724,#092536);
    box-shadow:inset 0 1px 0 rgba(255,255,255,.025);
}
.iz-closed-kpis small{
    display:block;
    color:#648ca1;
    font-size:8px;
    font-weight:800;
    letter-spacing:.85px;
    margin-bottom:4px;
}
.iz-closed-kpis b{
    color:#edf9fd;
    font-size:15px;
    font-weight:760;
}
.iz-closed-kpis b.pos{color:#43d9a0}
.iz-closed-kpis b.neg{color:#ff7181}

.iz-closed-table-shell{
    width:100%;
    border:1px solid #17445d;
    border-radius:13px;
    overflow:hidden;
    background:#06131f;
    box-shadow:0 14px 34px rgba(0,0,0,.16),inset 0 1px 0 rgba(255,255,255,.02);
}
.iz-closed-table-scroll{
    width:100%;
    overflow-x:auto;
    max-height:500px;
    overflow-y:auto;
}
.iz-closed-table{
    width:100%;
    min-width:1550px;
    border-collapse:separate;
    border-spacing:0;
    font-size:11px;
    color:#d8e8f0;
}
.iz-closed-table thead th{
    position:sticky;
    top:0;
    z-index:3;
    padding:10px 11px;
    text-align:left;
    white-space:nowrap;
    color:#74a7bd;
    background:#081a28;
    border-bottom:1px solid #1d4d64;
    font-size:8.5px;
    letter-spacing:.6px;
    text-transform:uppercase;
    font-weight:850;
}
.iz-closed-table tbody td{
    padding:10px 11px;
    border-bottom:1px solid rgba(30,70,91,.52);
    background:#071522;
    white-space:nowrap;
    vertical-align:middle;
}
.iz-closed-table tbody tr:nth-child(even) td{
    background:#081927;
}
.iz-closed-table tbody tr:hover td{
    background:#0a2434;
}
.iz-closed-table td.num{
    text-align:right;
    font-variant-numeric:tabular-nums;
}
.iz-closed-table td.center{text-align:center}
.iz-closed-table td.date{color:#8ca8b8;font-size:10px}
.iz-closed-table td.pos{color:#43d9a0;font-weight:800}
.iz-closed-table td.neg{color:#ff7181;font-weight:800}
.iz-closed-table td.neu{color:#a5bbc7}
.iz-closed-table td.pos-soft{color:#72dcb4}
.iz-closed-table td.neg-soft{color:#f18b98}

.iz-ticker-chip{
    display:inline-flex;
    padding:5px 8px;
    border-radius:7px;
    color:#dff9fc;
    background:#0b3143;
    border:1px solid #1b6479;
    font-weight:800;
    letter-spacing:.2px;
}
.iz-signal-chip{
    display:inline-flex;
    max-width:180px;
    overflow:hidden;
    text-overflow:ellipsis;
    padding:5px 7px;
    border-radius:7px;
    background:#0d2636;
    border:1px solid #244d61;
    color:#b8d8e5;
    font-weight:650;
}
.iz-close-reason{
    display:inline-flex;
    max-width:210px;
    overflow:hidden;
    text-overflow:ellipsis;
    padding:5px 7px;
    border-radius:7px;
    background:#251923;
    border:1px solid #653748;
    color:#f2c2cb;
    font-weight:650;
}
@media(max-width:850px){
    .iz-closed-kpis{grid-template-columns:repeat(2,minmax(0,1fr))}
}


/* v1.7.28 — Closed history insights */
.iz-closed-kpis-wide{
    grid-template-columns:repeat(4,minmax(0,1fr));
}
.iz-closed-insight-card{
    margin:0 0 13px;
    padding:15px 17px;
    border:1px solid #1a5068;
    border-radius:13px;
    background:linear-gradient(145deg,#071824,#0a2637);
    box-shadow:inset 0 1px 0 rgba(255,255,255,.025);
}
.iz-closed-insight-head{
    display:flex;
    align-items:flex-start;
    justify-content:space-between;
    gap:18px;
    margin-bottom:10px;
}
.iz-closed-insight-head small{
    display:block;
    color:#23d4de;
    font-size:8px;
    font-weight:850;
    letter-spacing:1.15px;
    margin-bottom:3px;
}
.iz-closed-insight-head h4{
    margin:0;
    color:#f1faff;
    font-size:16px;
}
.iz-closed-extremes{
    display:flex;
    flex-wrap:wrap;
    justify-content:flex-end;
    gap:6px;
}
.iz-closed-extremes span{
    padding:6px 8px;
    border-radius:7px;
    border:1px solid #1e4c61;
    background:#071522;
    color:#9bb9c8;
    font-size:9px;
    white-space:nowrap;
}
.iz-closed-extremes b{color:#dceef5}
.iz-closed-insight-card ul{
    margin:0;
    padding-left:18px;
    color:#c6dce6;
    font-size:11px;
    line-height:1.72;
}
.iz-closed-insight-card li{margin:3px 0}
.iz-close-reason-summary{
    margin:10px 0 3px;
    padding:10px 12px;
    border:1px solid #173f55;
    border-radius:10px;
    background:#071522;
}
.iz-close-reason-summary>small{
    display:block;
    color:#648ca1;
    font-size:8px;
    font-weight:850;
    letter-spacing:.85px;
    margin-bottom:7px;
}
.iz-close-reason-summary>div{
    display:flex;
    flex-wrap:wrap;
    gap:6px;
}
.iz-close-reason-summary span{
    display:inline-flex;
    gap:5px;
    padding:5px 7px;
    border-radius:7px;
    border:1px solid #244b5f;
    background:#0a1d2b;
    color:#8caaba;
    font-size:9px;
}
.iz-close-reason-summary b{color:#d6e8ef}
@media(max-width:900px){
    .iz-closed-kpis-wide{grid-template-columns:repeat(2,minmax(0,1fr))}
    .iz-closed-insight-head{flex-direction:column}
    .iz-closed-extremes{justify-content:flex-start}
}


/* v1.7.29 — Ana sayfa tıklanabilir hisse öğeleri */
.iz-home-stock-link{
    text-decoration:none!important;color:inherit!important;cursor:pointer!important;
    position:relative;transition:transform .16s ease,filter .16s ease!important;
}
.iz-home-stock-link:hover{
    transform:translateY(-2px)!important;filter:brightness(1.08)!important;
    outline:1px solid rgba(32,216,225,.52)!important;
}
.iz-open-detail{
    display:block!important;margin-top:5px!important;color:#80dce5!important;
    font-size:8px!important;font-weight:750!important;letter-spacing:.25px!important;opacity:.72;
}
.iz-home-stock-link:hover .iz-open-detail{opacity:1}
.iz-ticker-link{
    display:inline-flex;align-items:center;gap:5px;text-decoration:none!important;
    color:#dff9fc!important;padding:4px 7px;margin:-4px -7px;border-radius:7px;transition:.15s ease;
}
.iz-ticker-link span{color:#3fcbd8;font-size:9px;opacity:.65}
.iz-ticker-link:hover{background:#0a3042;color:#fff!important}
.iz-ticker-link:hover span{opacity:1}
.iz-mover-link{text-decoration:none!important;color:inherit!important;transition:background .15s ease!important}
.iz-mover-link:hover{background:#0a2636!important}
.iz-mini-arrow{margin-left:5px;color:#39cbd8;font-size:9px;opacity:.65}
.iz-mover-link:hover .iz-mini-arrow{opacity:1}


/* v1.7.30 — Same-session native home navigation */
.iz-native-pulse-card{
    min-height:100%;
}
.iz-native-map-head{
    display:flex;
    align-items:flex-start;
    justify-content:space-between;
    gap:12px;
    margin:0 0 10px;
    padding:13px 14px;
    border:1px solid #17445d;
    border-radius:12px;
    background:linear-gradient(145deg,#071724,#092536);
}
.iz-native-map-head>span{
    color:#4ecfe0;
    font-size:8px;
    font-weight:800;
    letter-spacing:.7px;
}
.iz-native-map-empty,
.iz-native-empty{
    padding:20px 12px;
    color:#7891a5;
    font-size:10px;
    border:1px dashed #1a4059;
    border-radius:10px;
    background:#071522;
}
.iz-native-map-empty{
    display:flex;
    flex-direction:column;
    align-items:center;
    text-align:center;
    gap:4px;
}
.iz-native-map-empty b{color:#b7c9d6}
.iz-native-section-title{
    margin:16px 0 8px;
    padding:11px 13px;
    border:1px solid #17445d;
    border-radius:11px;
    background:linear-gradient(145deg,#071724,#092536);
    color:#e9f7fc;
    font-size:11px;
    font-weight:850;
    letter-spacing:.9px;
}
.iz-native-th{
    padding:6px 5px;
    color:#648ca1;
    font-size:8px;
    font-weight:850;
    letter-spacing:.65px;
    text-transform:uppercase;
}
.iz-native-cell,
.iz-native-mover-cell{
    min-height:39px;
    display:flex;
    align-items:center;
    padding:0 6px;
    color:#c9dce5;
    font-size:10px;
    border-bottom:1px solid rgba(29,69,89,.45);
}
.iz-score-cell{
    color:#27dda0;
    font-weight:800;
}
.iz-native-mover-cell{
    justify-content:flex-end;
    min-height:38px;
}
[class*="st-key-home_signal_"] button,
[class*="st-key-home_mover_"] button{
    min-height:37px!important;
    border-radius:8px!important;
    background:#081b29!important;
    border:1px solid #17445d!important;
    color:#e1f4f8!important;
    font-size:10px!important;
    font-weight:760!important;
    justify-content:flex-start!important;
    padding-left:10px!important;
}
[class*="st-key-home_signal_"] button:hover,
[class*="st-key-home_mover_"] button:hover{
    border-color:#24cad6!important;
    background:#0a2b3d!important;
    color:#fff!important;
}


/* v1.7.31 — Premium home cards + stronger detail header */

.iz-detail-active-stock{
    margin:8px 0 14px;
    padding:13px 15px;
    border:1px solid #1b5e77;
    border-radius:12px;
    background:linear-gradient(135deg,#081d2b,#0b3042);
    box-shadow:inset 0 1px 0 rgba(255,255,255,.03),0 10px 24px rgba(0,0,0,.14);
}
.iz-detail-active-stock small{
    display:block;
    color:#4fd5df;
    font-size:8px;
    font-weight:850;
    letter-spacing:1px;
    margin-bottom:3px;
}
.iz-detail-active-stock strong{
    display:block;
    color:#ffffff;
    font-size:22px;
    line-height:1.1;
    letter-spacing:.2px;
    font-weight:800;
}
.iz-detail-active-stock span{
    display:block;
    margin-top:4px;
    color:#8fb0c0;
    font-size:10px;
}

/* selectbox içindeki seçili hisseyi de daha belirgin yap */
.st-key-detay_hisse_secici [data-baseweb="select"] > div{
    background:#081c2a!important;
    border:1px solid #1b6079!important;
    color:#f4fbff!important;
    min-height:46px!important;
}
.st-key-detay_hisse_secici [data-baseweb="select"] span,
.st-key-detay_hisse_secici [data-baseweb="select"] div{
    color:#f4fbff!important;
    opacity:1!important;
    font-weight:760!important;
}

/* Premium section heads */
.iz-premium-section-head{
    margin:18px 0 9px;
    padding:13px 15px;
    border:1px solid #17445d;
    border-radius:12px;
    background:linear-gradient(145deg,#071724,#092536);
    box-shadow:inset 0 1px 0 rgba(255,255,255,.025);
}
.iz-premium-section-head small{
    display:block;
    color:#32d3dc;
    font-size:8px;
    font-weight:850;
    letter-spacing:1.1px;
    margin-bottom:3px;
}
.iz-premium-section-head h3{
    margin:0;
    color:#effaff;
    font-size:16px;
    font-weight:780;
}
.iz-premium-section-head p{
    margin:4px 0 0;
    color:#7598aa;
    font-size:9px;
}

/* Signal board */
[class*="st-key-home_signal_"] button{
    min-height:43px!important;
    border-radius:9px!important;
    background:linear-gradient(135deg,#0a2334,#0c3144)!important;
    border:1px solid #1b5870!important;
    color:#f0fbff!important;
    font-size:11px!important;
    font-weight:800!important;
    justify-content:flex-start!important;
    padding-left:11px!important;
    box-shadow:inset 0 1px 0 rgba(255,255,255,.025)!important;
}
[class*="st-key-home_signal_"] button:hover{
    border-color:#2cd1dc!important;
    background:linear-gradient(135deg,#0c2d41,#0d3d50)!important;
    transform:translateY(-1px)!important;
}
.iz-premium-price{
    margin-top:4px;
    padding:6px 9px;
    border-radius:8px;
    background:#071522;
    border:1px solid #173e53;
    color:#9eb9c7;
    font-size:10px;
    text-align:center;
}
.iz-premium-signal-body{
    min-height:73px;
    display:grid;
    grid-template-columns:1.8fr .75fr .8fr .7fr;
    gap:8px;
    align-items:center;
    padding:9px 11px;
    border:1px solid #173e53;
    border-radius:10px;
    background:linear-gradient(145deg,#071522,#081c2a);
}
.iz-premium-signal-body>div{
    display:flex;
    flex-direction:column;
    gap:3px;
}
.iz-premium-signal-body span{
    color:#648ca1;
    font-size:8px;
    font-weight:800;
    letter-spacing:.55px;
}
.iz-premium-signal-body strong{
    color:#eaf8fc;
    font-size:12px;
    font-weight:780;
}
.iz-premium-risk{
    min-height:73px;
    display:flex;
    flex-direction:column;
    align-items:center;
    justify-content:center;
    gap:4px;
    border:1px solid #173e53;
    border-radius:10px;
    background:#071522;
}
.iz-premium-risk span{
    color:#648ca1;
    font-size:8px;
    font-weight:850;
    letter-spacing:.6px;
}
.iz-premium-risk b{
    color:#eaf8fc;
    font-size:11px;
}

/* Movers board */
[class*="st-key-home_mover_"] button{
    min-height:40px!important;
    border-radius:9px!important;
    background:linear-gradient(135deg,#0a2334,#0c3144)!important;
    border:1px solid #1b5870!important;
    color:#f0fbff!important;
    font-size:11px!important;
    font-weight:800!important;
    justify-content:flex-start!important;
    padding-left:11px!important;
}
[class*="st-key-home_mover_"] button:hover{
    border-color:#2cd1dc!important;
    background:linear-gradient(135deg,#0c2d41,#0d3d50)!important;
}
.iz-premium-mover-price,
.iz-premium-mover-change{
    min-height:40px;
    display:flex;
    align-items:center;
    justify-content:center;
    border:1px solid #173e53;
    border-radius:9px;
    background:#071522;
    color:#c9dce5;
    font-size:10px;
    font-weight:700;
}
.iz-premium-mover-change.up{
    color:#39dfa0;
    border-color:#195d4b;
    background:linear-gradient(135deg,#071c1a,#0b2a22);
}
.iz-premium-mover-change.down{
    color:#ff7080;
    border-color:#623344;
    background:linear-gradient(135deg,#1b1117,#26151d);
}

/* Fırsat haritası başlığı daha güçlü */
.iz-native-map-head{
    padding:15px 16px!important;
    background:linear-gradient(145deg,#071724,#0a2b3d)!important;
    border-color:#1b5870!important;
    box-shadow:inset 0 1px 0 rgba(255,255,255,.03),0 10px 22px rgba(0,0,0,.14)!important;
}

</style>
""", unsafe_allow_html=True)

# --- ÖNBELLEKSİZ ÖZEL HTTP OTURUMU ---
session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Cache-Control": "no-cache, no-store, must-revalidate",
    "Pragma": "no-cache",
    "Expires": "0"
})

# --- ÇEREZ YÖNETİCİSİ (COOKIE MANAGER) ---
# Eski düz e-posta cookie'si güvenilir oturum sayılmaz. "Beni hatırla" yalnızca
# Firebase Admin'in imzaladığı session cookie ile çalışır.
cookie_manager = stx.CookieManager(key="cookie_manager")
saved_session_cookie = cookie_manager.get(cookie="izfin_session")
try:
    _legacy_email_cookie = cookie_manager.get(cookie="user_email")
    if _legacy_email_cookie:
        cookie_manager.delete("user_email")
except Exception:
    pass

# --- FIREBASE BAŞLATMA ---
if not firebase_admin._apps:
    try:
        if "firebase" in st.secrets:
            firebase_secrets = dict(st.secrets["firebase"])
            cred = credentials.Certificate(firebase_secrets)
        else:
            cred = credentials.Certificate("serviceAccountKey.json")
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.warning(f"Firebase başlatılamadı (Veritabanı özellikleri devre dışı): {e}")

try:
    db = firestore.client()
except Exception:
    db = None

# --- FIREBASE AUTH: GERÇEK E-POSTA/ŞİFRE OTURUMU ---
def _firebase_web_api_key():
    try:
        key = st.secrets.get("FIREBASE_WEB_API_KEY", "")
    except Exception:
        key = ""
    if not key:
        key = os.getenv("FIREBASE_WEB_API_KEY", "")
    if not key:
        try:
            if "firebase_web" in st.secrets:
                key = dict(st.secrets["firebase_web"]).get("apiKey", "")
        except Exception:
            pass
    return str(key or "").strip()

FIREBASE_WEB_API_KEY = _firebase_web_api_key()
FIREBASE_AUTH_BASE = "https://identitytoolkit.googleapis.com/v1"


def _firebase_project_id():
    try:
        if "firebase" in st.secrets:
            return str(dict(st.secrets["firebase"]).get("project_id", "") or "").strip()
    except Exception:
        pass
    return str(os.getenv("FIREBASE_PROJECT_ID", "") or "").strip()

FIREBASE_PROJECT_ID = _firebase_project_id()
FIREBASE_AUTH_DOMAIN = f"{FIREBASE_PROJECT_ID}.firebaseapp.com" if FIREBASE_PROJECT_ID else ""


def _secret_degeri(ad, varsayilan=""):
    try:
        v = st.secrets.get(ad, varsayilan)
    except Exception:
        v = os.getenv(ad, varsayilan)
    return str(v or varsayilan).strip()

GOOGLE_OAUTH_CLIENT_ID = _secret_degeri("GOOGLE_OAUTH_CLIENT_ID")
GOOGLE_OAUTH_CLIENT_SECRET = _secret_degeri("GOOGLE_OAUTH_CLIENT_SECRET")
GOOGLE_OAUTH_REDIRECT_URI = _secret_degeri(
    "GOOGLE_OAUTH_REDIRECT_URI",
    "https://yenibotsaldeneme-3mevwlpzmsq8khknqxxyuf.streamlit.app/",
)
GOOGLE_OAUTH_AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_OAUTH_TOKEN_URL = "https://oauth2.googleapis.com/token"


def _firebase_auth_hata_mesaji(kod):
    kod = str(kod or "").split(" : ")[0].strip()
    return {
        "EMAIL_EXISTS": "Bu e-posta adresiyle zaten bir hesap var.",
        "EMAIL_NOT_FOUND": "Bu e-posta ile kayıtlı hesap bulunamadı.",
        "INVALID_PASSWORD": "Şifre hatalı.",
        "INVALID_LOGIN_CREDENTIALS": "E-posta veya şifre hatalı.",
        "USER_DISABLED": "Bu kullanıcı hesabı devre dışı bırakılmış.",
        "INVALID_EMAIL": "Geçerli bir e-posta adresi girin.",
        "WEAK_PASSWORD": "Şifre yeterince güçlü değil.",
        "TOO_MANY_ATTEMPTS_TRY_LATER": "Çok fazla başarısız deneme yapıldı. Bir süre sonra tekrar deneyin.",
        "OPERATION_NOT_ALLOWED": "Firebase'de Email/Password giriş yöntemi etkin değil.",
    }.get(kod, f"Kimlik doğrulama başarısız: {kod or 'bilinmeyen hata'}")

def _firebase_auth_post(action, payload):
    if not FIREBASE_WEB_API_KEY:
        return None, "FIREBASE_WEB_API_KEY eksik. Streamlit secrets'e Firebase Web API Key eklenmeli."
    try:
        r = requests.post(
            f"{FIREBASE_AUTH_BASE}/accounts:{action}?key={FIREBASE_WEB_API_KEY}",
            json=payload,
            timeout=10,
        )
        data = r.json() if r.content else {}
        if r.ok:
            return data, None
        kod = ((data.get("error") or {}).get("message") or f"HTTP_{r.status_code}")
        return None, _firebase_auth_hata_mesaji(kod)
    except Exception as e:
        return None, f"Firebase Authentication bağlantısı kurulamadı: {e}"

def _kullanici_liste_doc_id():
    uid = str(st.session_state.get("user_uid") or "").strip()
    return uid or str(st.session_state.get("user_email") or "").strip().lower()

def _kullanici_profilini_hazirla(uid, email):
    if not db or not uid:
        return
    try:
        db.collection("kullanicilar").document(uid).set({
            "uid": uid, "email": email, "son_giris": datetime.now().isoformat(),
        }, merge=True)
    except Exception as e:
        logging.getLogger("IZFIN").exception("Kullanıcı profili yazılamadı: %s", e)

def _oturum_ac(data, beni_hatirla=False):
    id_token = str((data or {}).get("idToken") or "")
    if not id_token:
        return False, "Firebase ID token alınamadı."
    try:
        claims = auth.verify_id_token(id_token)
        uid = str(claims.get("uid") or (data or {}).get("localId") or "")
        email = str(claims.get("email") or (data or {}).get("email") or "").strip().lower()
        if not uid or not email:
            return False, "Kullanıcı kimliği doğrulanamadı."
        st.session_state.user_uid = uid
        st.session_state.user_email = email
        st.session_state.logout_triggered = False
        st.session_state.kullanici_listesi_yuklendi = False
        _kullanici_profilini_hazirla(uid, email)
        try:
            cookie_manager.delete("izfin_session")
        except Exception:
            pass
        if beni_hatirla:
            expires_in = timedelta(days=14)
            session_cookie = auth.create_session_cookie(id_token, expires_in=expires_in)
            cookie_manager.set("izfin_session", session_cookie, expires_at=datetime.now() + expires_in)
        return True, None
    except Exception as e:
        izfin_hata_logla("firebase_id_token_dogrulama", e)
        return False, "Güvenli oturum oluşturulamadı. Lütfen tekrar giriş yapın."

def _kayit_ol(email, password):
    data, err = _firebase_auth_post("signUp", {"email": email, "password": password, "returnSecureToken": True})
    if err:
        return None, err
    uid = str(data.get("localId") or "")
    if db and uid:
        try:
            db.collection("kullanicilar").document(uid).set({
                "uid": uid, "email": email, "olusturma_zamani": datetime.now().isoformat(), "son_giris": None,
            }, merge=True)
        except Exception as e:
            izfin_hata_logla("kayit_profil_firestore", e)
        try:
            db.collection("kullanici_listeleri").document(uid).set({
                "uid": uid,
                "email": email,
                "tickers": VARSAYILAN_TICKERS.copy(),
                "guncelleme_zamani": datetime.now().isoformat(),
            }, merge=True)
        except Exception as e:
            izfin_hata_logla("kayit_ilk_kisisel_liste", e)
    try:
        _firebase_auth_post("sendOobCode", {"requestType": "VERIFY_EMAIL", "idToken": data.get("idToken")})
    except Exception:
        pass
    return data, None

def _sifre_sifirlama_maili(email):
    _, err = _firebase_auth_post("sendOobCode", {"requestType": "PASSWORD_RESET", "email": email})
    return err

def _captcha_yenile():
    st.session_state.captcha_a = pysecrets.randbelow(8) + 2
    st.session_state.captcha_b = pysecrets.randbelow(8) + 2
    st.session_state.captcha_nonce = pysecrets.token_hex(6)

def _captcha_hazirla():
    if "captcha_a" not in st.session_state or "captcha_b" not in st.session_state:
        _captcha_yenile()

if "user_uid" not in st.session_state:
    st.session_state.user_uid = None
if "user_email" not in st.session_state:
    st.session_state.user_email = None
if "logout_triggered" not in st.session_state:
    st.session_state.logout_triggered = False

if (not st.session_state.user_email) and saved_session_cookie and not st.session_state.logout_triggered:
    try:
        claims = auth.verify_session_cookie(str(saved_session_cookie), check_revoked=True)
        uid = str(claims.get("uid") or "")
        user = auth.get_user(uid) if uid else None
        email = str((claims.get("email") if claims else None) or (user.email if user else "") or "").strip().lower()
        if uid and email:
            st.session_state.user_uid = uid
            st.session_state.user_email = email
            st.session_state.kullanici_listesi_yuklendi = False
            _kullanici_profilini_hazirla(uid, email)
    except Exception:
        try:
            cookie_manager.delete("izfin_session")
        except Exception:
            pass
        st.session_state.user_uid = None
        st.session_state.user_email = None

VARSAYILAN_TICKERS = ["AAPL", "MSFT", "TSLA", "NVDA", "AMD", "INTC", "THYAO.IS", "FROTO.IS", "TOASO.IS"]

# --- IZFIN STRATEJİ SÜRÜMÜ ---
STRATEJI_SURUMU = "IZFIN-v1.7.5-auth-switch-fixed"
PERFORMANS_UFUKLARI = (1, 5, 10, 20, 45)

# --- IZFIN UYGULAMA SÜRÜMÜ / LOG ---
IZFIN_APP_SURUMU = "v1.7.2 Signature UI"
logger = logging.getLogger("IZFIN")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)

# Finnhub isteklerini süreç içinde ortak hız sınırına tabi tut.
# Plan bazlı dakika limitleri değişebildiği için 429 yanıtlarında ayrıca backoff uygulanır.
_FINNHUB_RATE_LOCK = Lock()
_FINNHUB_LAST_CALL = 0.0
_FINNHUB_MIN_INTERVAL = 0.10  # yaklaşık 10 istek/sn; 30/sn üst sınırının oldukça altında


def izfin_hata_logla(baglam, hata, ticker=None):
    """Kullanıcıya traceback göstermeden Streamlit Cloud loglarına teknik hata yazar."""
    etiket = f"{baglam} | {ticker}" if ticker else baglam
    logger.exception("IZFIN hata [%s]: %s", etiket, hata)
    try:
        if "taramada_hatalar" not in st.session_state:
            st.session_state.taramada_hatalar = []
        st.session_state.taramada_hatalar.append({
            "baglam": baglam, "ticker": ticker, "tip": type(hata).__name__,
            "mesaj": str(hata)[:180]
        })
    except Exception:
        pass

# --- HAZIR VARLIK LİSTELERİ ---
BIST_30 = [
    "AKBNK.IS", "ALARK.IS", "ASELS.IS", "ASTOR.IS", "BIMAS.IS", "BRISA.IS",
    "CCOLA.IS", "ENKAI.IS", "EREGL.IS", "FROTO.IS", "GARAN.IS", "GUBRF.IS",
    "HEKTS.IS", "ISCTR.IS", "KCHOL.IS", "KONTR.IS", "KOZAA.IS", "KOZAL.IS",
    "KRDMD.IS", "OYAKC.IS", "PETKM.IS", "PGSUS.IS", "SAHOL.IS", "SASA.IS",
    "SISE.IS", "TCELL.IS", "THYAO.IS", "TOASO.IS", "TUPRS.IS", "YKBNK.IS"
]

BIST_100 = sorted(set(BIST_30 + [
    "AGHOL.IS", "AHGAZ.IS", "AKCNS.IS", "AKFGY.IS", "AKSA.IS", "AKSEN.IS",
    "ALBRK.IS", "ALFAS.IS", "ARCLK.IS", "ASUZU.IS", "BAGFS.IS", "BIOEN.IS",
    "BOBET.IS", "BRYAT.IS", "BUCIM.IS", "CANTE.IS", "CIMSA.IS", "CWENE.IS",
    "DOAS.IS", "DOHOL.IS", "ECZYT.IS", "EGEEN.IS", "EKGYO.IS", "ENERY.IS",
    "EUPWR.IS", "ENJSA.IS", "FORMT.IS", "GESAN.IS", "GLYHO.IS", "GWIND.IS",
    "HALKB.IS", "IPEKE.IS", "ISDMR.IS", "ISGYO.IS", "KAYSE.IS", "KMPUR.IS",
    "KONYA.IS", "KOTON.IS", "KZBGY.IS", "MAVI.IS", "MGROS.IS", "ODAS.IS",
    "ONCSM.IS", "OTKAR.IS", "PENTA.IS", "PSGYO.IS", "REEDR.IS", "SMRTG.IS",
    "SOKM.IS", "TAVHL.IS", "TKFEN.IS", "TMSN.IS", "TSKB.IS", "TTKOM.IS",
    "TTRAK.IS", "ULKER.IS", "VAKBN.IS", "VESBE.IS", "VESTL.IS", "YEOTK.IS",
    "ZOREN.IS"
]))

ABD_HİSSELERİ = ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "NVDA", "AMD", "INTC", "NFLX"]

# --- OTURUM DURUMU (SESSION STATE) ---
if "opsiyon_sonuclar" not in st.session_state:
    st.session_state.opsiyon_sonuclar = None

# --- HİBRİT VERİ ÇEKME MOTORU (YFINANCE + FINNHUB) ---
FINNHUB_API_KEY = st.secrets.get("FINNHUB_API_KEY", os.getenv("FINNHUB_API_KEY", ""))
FINNHUB_BASE_URL = "https://finnhub.io/api/v1"

def _normalize_yf_columns(df):
    if isinstance(df, pd.DataFrame) and isinstance(df.columns, pd.MultiIndex):
        df = df.copy()
        df.columns = df.columns.get_level_values(0)
    return df

def _finnhub_symbol(ticker):
    # Finnhub ücretsiz planda ABD hisseleri güvenilir biçimde desteklenir.
    # BIST sembollerinde kapsama sınırlı olabildiği için Yahoo fallback kullanılır.
    return ticker.replace(".IS", "") if ticker.endswith(".IS") else ticker

@st.cache_data(ttl=21600, show_spinner=False)
def peg_degeri_cek(ticker):
    """Yahoo Finance temel verisinden standart/trailing PEG değerini okur.

    PEG teknik skora dahil edilmez; yalnızca temel değerleme etiketi olarak kullanılır.
    Geçersiz, negatif veya ulaşılamayan değerlerde None döner.
    """
    try:
        info = yf.Ticker(ticker).get_info() or {}
        # Yahoo/yfinance sürümüne göre anahtar adı değişebildiği için iki yaygın
        # trailing/standart PEG alanını kontrollü biçimde deniyoruz.
        raw = info.get("trailingPegRatio")
        if raw is None:
            raw = info.get("pegRatio")
        if raw is None:
            return None
        peg = float(raw)
        if not np.isfinite(peg) or peg <= 0:
            return None
        return peg
    except Exception:
        return None


def peg_yorumu(peg):
    """PEG'i skorlamadan, yalnızca açıklayıcı değerleme etiketi üretir."""
    if peg is None or not np.isfinite(peg) or peg <= 0:
        return "—", "⚪ PEG değerlendirilemedi"
    if peg < 0.75:
        etiket = "💎 Çok Ucuz Büyüme"
    elif peg < 1.00:
        etiket = "🟢 Ucuz Büyüme"
    elif peg < 1.50:
        etiket = "✅ Makul Büyüme Değerlemesi"
    elif peg < 2.00:
        etiket = "🟡 Büyüme Primi Var"
    else:
        etiket = "🟠 Yüksek Büyüme Primi"
    return f"{peg:.2f}", etiket


def peg_verilerini_paralel_cek(tickers, max_workers=6):
    """PEG sorgularını taramanın geri kalanını mümkün olduğunca yavaşlatmadan paralel çeker."""
    tickers = list(dict.fromkeys(tickers or []))
    if not tickers:
        return {}
    sonuc = {}
    with ThreadPoolExecutor(max_workers=min(max_workers, len(tickers))) as executor:
        futures = {executor.submit(peg_degeri_cek, t): t for t in tickers}
        for future in as_completed(futures):
            ticker = futures[future]
            try:
                sonuc[ticker] = future.result()
            except Exception:
                sonuc[ticker] = None
    return sonuc


def _finnhub_get(endpoint, params, timeout=3, max_retry=2):
    if not FINNHUB_API_KEY:
        return None

    global _FINNHUB_LAST_CALL

    for deneme in range(max_retry + 1):
        try:
            # ThreadPool olsa bile istek başlangıçlarını süreç içinde aralıklı gönder.
            with _FINNHUB_RATE_LOCK:
                simdi = time.monotonic()
                bekle = _FINNHUB_MIN_INTERVAL - (simdi - _FINNHUB_LAST_CALL)
                if bekle > 0:
                    time.sleep(bekle)
                _FINNHUB_LAST_CALL = time.monotonic()

            r = session.get(
                f"{FINNHUB_BASE_URL}/{endpoint}",
                params={**params, "token": FINNHUB_API_KEY},
                timeout=timeout,
            )

            if r.status_code == 429:
                # Retry-After varsa onu kullan, yoksa kontrollü artan bekleme.
                try:
                    retry_after = float(r.headers.get("Retry-After", 0) or 0)
                except Exception:
                    retry_after = 0.0
                if deneme < max_retry:
                    time.sleep(max(retry_after, 1.0 + deneme * 1.5))
                    continue
                return None

            r.raise_for_status()
            data = r.json()
            return data if isinstance(data, dict) else None

        except Exception as e:
            if deneme < max_retry:
                time.sleep(0.5 * (deneme + 1))
                continue
            izfin_hata_logla("finnhub_get", e)
            return None

    return None

@st.cache_data(ttl=900, show_spinner=False)
def taze_veri_indir(tickers_tuple):
    try:
        data = yf.download(
            list(tickers_tuple),
            period="400d",
            group_by="ticker",
            progress=False,
            threads=True,
            auto_adjust=True,
                        timeout=10,
        )
        return data
    except Exception as e:
        izfin_hata_logla("yahoo_toplu_gunluk", e)
        return pd.DataFrame()

@st.cache_data(ttl=20, show_spinner=False)
def finnhub_quote_cek(ticker):
    if ticker.endswith(".IS"):
        return None
    data = _finnhub_get("quote", {"symbol": _finnhub_symbol(ticker)})
    if not data or not data.get("c"):
        return None
    return {
        "open": float(data.get("o") or 0),
        "high": float(data.get("h") or 0),
        "low": float(data.get("l") or 0),
        "close": float(data.get("c") or 0),
        "previous_close": float(data.get("pc") or 0),
        "timestamp": int(data.get("t") or 0),
        "source": "Finnhub",
    }

def _intraday_local_index(ticker, df):
    if df is None or df.empty:
        return pd.DataFrame()
    x = df.copy().sort_index()
    try:
        idx = pd.to_datetime(x.index)
        tz = "Europe/Istanbul" if str(ticker).endswith(".IS") else "America/New_York"
        if getattr(idx, "tz", None) is None:
            idx = idx.tz_localize(tz)
        else:
            idx = idx.tz_convert(tz)
        x.index = idx
    except Exception:
        pass
    return x


def regular_seans_intraday(ticker, df):
    """Teknik hesaplarda yalnızca normal seans mumlarını kullanır."""
    x = _intraday_local_index(ticker, df)
    if x.empty:
        return x
    try:
        if str(ticker).endswith(".IS"):
            return x.between_time("10:00", "18:10", inclusive="both")
        return x.between_time("09:30", "16:00", inclusive="both")
    except Exception:
        return x


def abd_quote_regular_seans_mi(quote):
    if not quote:
        return False
    try:
        ts = int(quote.get("timestamp") or 0)
        if ts <= 0:
            return False
        dt = datetime.fromtimestamp(ts, tz=ZoneInfo("America/New_York"))
        dakika = dt.hour * 60 + dt.minute
        return dt.weekday() < 5 and (9 * 60 + 30) <= dakika <= (16 * 60)
    except Exception:
        return False


def seans_disi_ozet(ticker, ham_intraday, quote=None):
    """ABD premarket/after-hours fiyatını yalnızca ek bilgi olarak verir."""
    if str(ticker).endswith(".IS"):
        return "—", None
    x = _intraday_local_index(ticker, ham_intraday)
    if x.empty or "Close" not in x.columns:
        if quote and quote.get("close", 0) > 0 and not abd_quote_regular_seans_mi(quote):
            try:
                px = float(quote["close"])
                return f"🌙 Seans dışı {px:.2f}", px
            except Exception:
                pass
        return "—", None
    try:
        x = x.dropna(subset=["Close"]).sort_index()
        if x.empty:
            return "—", None
        son_ts = x.index[-1]
        son_dakika = son_ts.hour * 60 + son_ts.minute
        if (9 * 60 + 30) <= son_dakika <= (16 * 60):
            return "—", None
        son_fiyat = float(x["Close"].iloc[-1])
        tur = "PM" if son_dakika < (9 * 60 + 30) else "AH"
        regular = regular_seans_intraday(ticker, x)
        onceki_regular = regular[regular.index < son_ts] if not regular.empty else regular
        if not onceki_regular.empty:
            ref = float(onceki_regular["Close"].dropna().iloc[-1])
            if ref > 0:
                deg = ((son_fiyat / ref) - 1.0) * 100.0
                return f"🌙 {tur} {son_fiyat:.2f} ({deg:+.2f}%)", son_fiyat
        return f"🌙 {tur} {son_fiyat:.2f}", son_fiyat
    except Exception:
        return "—", None


@st.cache_data(ttl=20, show_spinner=False)
def intraday_veri_cek(ticker, interval="5m", period="5d"):
    try:
        df = yf.download(
            ticker,
            period=period,
            interval=interval,
            progress=False,
            prepost=True,
            auto_adjust=True,
                    )
        return _normalize_yf_columns(df)
    except Exception as e:
        izfin_hata_logla("yahoo_intraday_tekil", e, ticker)
        return pd.DataFrame()


@st.cache_data(ttl=30, show_spinner=False)
def toplu_intraday_veri_cek(tickers_tuple, interval="5m", period="5d"):
    """Tüm varlıkların gün içi verisini tek Yahoo isteğinde indirir."""
    if not tickers_tuple:
        return pd.DataFrame()
    try:
        return yf.download(
            list(tickers_tuple),
            period=period,
            interval=interval,
            group_by="ticker",
            progress=False,
            prepost=True,
            threads=True,
            auto_adjust=True,
                        timeout=8,
        )
    except Exception as e:
        izfin_hata_logla("yahoo_intraday_toplu", e)
        return pd.DataFrame()


def toplu_veriden_ticker_ayir(toplu_df, ticker, toplam_adet):
    if toplu_df is None or toplu_df.empty:
        return pd.DataFrame()
    try:
        if toplam_adet == 1 and not isinstance(toplu_df.columns, pd.MultiIndex):
            return _normalize_yf_columns(toplu_df.copy())
        if isinstance(toplu_df.columns, pd.MultiIndex):
            # group_by='ticker' biçimi
            if ticker in toplu_df.columns.get_level_values(0):
                return _normalize_yf_columns(toplu_df[ticker].copy())
            # Bazı yfinance sürümlerinde ticker ikinci seviyede olabilir.
            if ticker in toplu_df.columns.get_level_values(-1):
                return _normalize_yf_columns(toplu_df.xs(ticker, axis=1, level=-1).copy())
    except Exception:
        pass
    return pd.DataFrame()


def gunluk_toplu_veriden_ticker_ayir(toplu_df, ticker, toplam_adet):
    """Yahoo'nun tek/çok sembolde değişebilen kolon düzenini güvenle ayırır."""
    return toplu_veriden_ticker_ayir(toplu_df, ticker, toplam_adet)


def _yalnizca_kapali_mumlar(df, varsayilan_dakika=5):
    """Son bar gerçekten oluşuyorsa çıkarır; kapanmış son barı gereksiz yere silmez."""
    if df is None or df.empty:
        return pd.DataFrame()
    x = df.copy().sort_index()
    if len(x) < 2:
        return x.iloc[0:0]
    try:
        idx = pd.DatetimeIndex(pd.to_datetime(x.index))
        farklar = idx.to_series().diff().dropna()
        pozitif = farklar[farklar > pd.Timedelta(0)]
        bar_suresi = pozitif.tail(20).median() if not pozitif.empty else pd.Timedelta(minutes=varsayilan_dakika)
        if pd.isna(bar_suresi) or bar_suresi <= pd.Timedelta(0):
            bar_suresi = pd.Timedelta(minutes=varsayilan_dakika)
        son = idx[-1]
        simdi = pd.Timestamp.now(tz=son.tz) if son.tz is not None else pd.Timestamp.now()
        # Küçük veri gecikmelerini tolere et; yalnızca halen oluşan barı dışarıda bırak.
        if simdi < son + bar_suresi + pd.Timedelta(seconds=10):
            return x.iloc[:-1].copy()
    except Exception:
        # Zaman bilgisi yorumlanamazsa ileriye bakış riskine karşı muhafazakâr davran.
        return x.iloc[:-1].copy()
    return x


def finnhub_quotelari_paralel_cek(tickers, max_workers=6):
    """ABD hisselerinin quote verisini paralel çeker; BIST Yahoo ile devam eder."""
    abd = [t for t in tickers if not str(t).endswith('.IS')]
    sonuc = {t: None for t in tickers}
    if not FINNHUB_API_KEY or not abd:
        return sonuc
    with ThreadPoolExecutor(max_workers=min(max_workers, len(abd))) as executor:
        futures = {executor.submit(finnhub_quote_cek, t): t for t in abd}
        for future in as_completed(futures):
            t = futures[future]
            try:
                sonuc[t] = future.result()
            except Exception:
                sonuc[t] = None
    return sonuc

def canli_ohlcv_ile_guncelle(ticker, df_long, intraday_hazir=None, quote_hazir=None):
    """Günlük seriyi yalnızca NORMAL SEANS verisiyle günceller."""
    df = df_long.copy().sort_index()
    kaynak = "Yahoo günlük (fallback)"
    quote = quote_hazir if quote_hazir is not None else finnhub_quote_cek(ticker)
    ham_intraday = intraday_hazir.copy() if isinstance(intraday_hazir, pd.DataFrame) else pd.DataFrame()
    if ham_intraday.empty:
        ham_intraday = intraday_veri_cek(ticker, interval="5m", period="5d")
    ham_intraday = _normalize_yf_columns(ham_intraday)
    intraday = regular_seans_intraday(ticker, ham_intraday)
    if not intraday.empty and "Close" in intraday.columns:
        intraday = intraday.dropna(subset=["Close"]).sort_index()
    if not intraday.empty:
        seans_tarihi = intraday.index[-1].date()
        seans_rows = intraday[intraday.index.date == seans_tarihi]
        if not seans_rows.empty:
            o = float(seans_rows["Open"].dropna().iloc[0])
            h = float(seans_rows["High"].max())
            l = float(seans_rows["Low"].min())
            c = float(seans_rows["Close"].dropna().iloc[-1])
            v = float(seans_rows["Volume"].fillna(0).sum()) if "Volume" in seans_rows else 0.0
            kaynak = "Yahoo 5 dk (BIST normal seans)" if ticker.endswith(".IS") else "Yahoo 5 dk (ABD normal seans)"
            if (not ticker.endswith(".IS")) and quote and quote.get("close", 0) > 0 and abd_quote_regular_seans_mi(quote):
                c = float(quote["close"])
                if quote.get("open", 0) > 0: o = float(quote["open"])
                if quote.get("high", 0) > 0: h = max(h, float(quote["high"]))
                if quote.get("low", 0) > 0: l = min(l, float(quote["low"]))
                kaynak = "Finnhub fiyat + Yahoo 5 dk (normal seans)"
            last_daily_date = pd.Timestamp(df.index[-1]).date()
            if last_daily_date == seans_tarihi:
                target_idx = df.index[-1]
            else:
                target_idx = pd.Timestamp(seans_tarihi)
                if getattr(df.index, "tz", None) is not None:
                    target_idx = target_idx.tz_localize(df.index.tz)
            row = {"Open": o, "High": h, "Low": l, "Close": c, "Volume": v}
            for col, val in row.items():
                if col in df.columns and pd.notna(val):
                    df.loc[target_idx, col] = val
            df = df.sort_index()
    elif quote and quote.get("close", 0) > 0:
        # Quote-only fallback geçmiş günlük mumu bozmaz.
        kaynak = "Yahoo günlük · Finnhub quote yalnızca ek fiyat"
    return df, intraday, kaynak, ham_intraday

def tekil_taze_veri_cek(ticker):
    """Yalnızca toplu intraday başarısızlığında normal-seans fallback."""
    return regular_seans_intraday(ticker, intraday_veri_cek(ticker, interval="5m", period="5d"))


def tetik_puani_hesapla(intraday, uzun_vade_trend):
    """Kapanmış 5 dakikalık mumlarla 0-100 arası tetik kalitesi hesaplar.

    Puan bileşenleri:
    - Önceki 20 mum direncinin kırılması: 25
    - Hacmin önceki 20 mum ortalamasının en az %130'u olması: 20
    - EMA9 > EMA21: 15
    - MACD > sinyal çizgisi: 15
    - RSI 50-70 aralığı: 10
    - Pozitif ve üst bölgede kapanan kaliteli mum: 10
    - Günlük ana trendin yukarı olması: 5

    En son 5 dakikalık mum oluşuyor olabileceği için hesaplamadan çıkarılır.
    Böylece değişen, henüz kapanmamış mumun yanlış tetik üretmesi engellenir.
    """
    bos = {
        "puan": 0,
        "seviye": "⏳ TETİK YOK",
        "mesaj": "⏳ TETİK YOK: Yeterli kapanmış 5 dakikalık veri bulunamadı",
        "detay": [],
        "direnc": None,
        "hacim_orani": 0.0,
        "rsi": None,
        "mum_kalitesi": 0.0,
        "sahte_kirilim": False,
    }
    if intraday is None or intraday.empty:
        return bos

    gerekli = {"Open", "High", "Low", "Close", "Volume"}
    if not gerekli.issubset(intraday.columns):
        return bos

    df = intraday[list(gerekli)].copy().sort_index()
    df = df.replace([np.inf, -np.inf], np.nan).dropna(subset=["Open", "High", "Low", "Close"])
    if len(df) < 24:
        return bos

    # Yalnızca gerçekten oluşmakta olan son mum dışarıda bırakılır. Piyasa kapalıyken
    # tamamlanmış son mumu silmek, giriş motorunu bir bar geriden çalıştırıyordu.
    kapali = _yalnizca_kapali_mumlar(df)
    if len(kapali) < 22:
        return bos

    sinyal_mumu = kapali.iloc[-1]
    onceki = kapali.iloc[:-1]
    onceki_20 = onceki.tail(20)

    direnc = float(onceki_20["High"].max())
    hacim_ort = float(onceki_20["Volume"].replace(0, np.nan).mean())
    son_hacim = float(sinyal_mumu["Volume"] or 0)
    hacim_orani = son_hacim / hacim_ort if np.isfinite(hacim_ort) and hacim_ort > 0 else 0.0

    close = kapali["Close"].astype(float)
    ema9 = close.ewm(span=9, adjust=False).mean()
    ema21 = close.ewm(span=21, adjust=False).mean()
    macd = close.ewm(span=12, adjust=False).mean() - close.ewm(span=26, adjust=False).mean()
    macd_signal = macd.ewm(span=9, adjust=False).mean()
    rsi_serisi = _rsi_serisi(close)

    son_close = float(sinyal_mumu["Close"])
    son_open = float(sinyal_mumu["Open"])
    son_high = float(sinyal_mumu["High"])
    son_low = float(sinyal_mumu["Low"])
    rsi = float(rsi_serisi.iloc[-1]) if pd.notna(rsi_serisi.iloc[-1]) else 50.0

    mum_araligi = max(son_high - son_low, 1e-9)
    govde_orani = abs(son_close - son_open) / mum_araligi
    kapanis_konumu = (son_close - son_low) / mum_araligi
    ust_fitil_orani = (son_high - max(son_open, son_close)) / mum_araligi

    kirilim = son_close > direnc
    hacim_guclu = hacim_orani >= 1.30
    ema_uyumu = bool(ema9.iloc[-1] > ema21.iloc[-1])
    macd_uyumu = bool(macd.iloc[-1] > macd_signal.iloc[-1])
    rsi_uyumu = 50 <= rsi <= 70
    kaliteli_mum = son_close > son_open and kapanis_konumu >= 0.70 and govde_orani >= 0.45
    sahte_kirilim = son_high > direnc and son_close <= direnc and ust_fitil_orani >= 0.30

    puan = 0
    detay = []

    if kirilim:
        puan += 25
        detay.append("✅ Önceki 20 mum direnci kırıldı (+25)")
    else:
        detay.append("⚪ Önceki 20 mum direnci henüz kapanışla kırılmadı (+0)")

    if hacim_guclu:
        puan += 20
        detay.append(f"✅ Hacim ortalamanın %{hacim_orani*100:.0f}'i (+20)")
    elif hacim_orani >= 1.10:
        puan += 10
        detay.append(f"🟡 Hacim kısmen güçlü: %{hacim_orani*100:.0f} (+10)")
    else:
        detay.append(f"⚪ Hacim teyidi zayıf: %{hacim_orani*100:.0f} (+0)")

    if ema_uyumu:
        puan += 15
        detay.append("✅ EMA9, EMA21 üzerinde (+15)")
    else:
        detay.append("⚪ EMA9/EMA21 kısa trend teyidi yok (+0)")

    if macd_uyumu:
        puan += 15
        detay.append("✅ 5 dk MACD sinyal çizgisinin üzerinde (+15)")
    else:
        detay.append("⚪ 5 dk MACD teyidi yok (+0)")

    if rsi_uyumu:
        puan += 10
        detay.append(f"✅ 5 dk RSI uygun bölgede: {rsi:.1f} (+10)")
    elif 45 <= rsi < 50 or 70 < rsi <= 75:
        puan += 5
        detay.append(f"🟡 5 dk RSI sınır bölgede: {rsi:.1f} (+5)")
    else:
        detay.append(f"⚪ 5 dk RSI uygun değil: {rsi:.1f} (+0)")

    if kaliteli_mum:
        puan += 10
        detay.append("✅ Mum pozitif ve üst bölgede güçlü kapandı (+10)")
    else:
        detay.append("⚪ Mum gövdesi/kapanış kalitesi yetersiz (+0)")

    if uzun_vade_trend:
        puan += 5
        detay.append("✅ Günlük ana trend yukarı (+5)")
    else:
        detay.append("⚪ Günlük ana trend teyidi yok (+0)")

    puan = int(max(0, min(100, puan)))
    if puan >= 80:
        seviye = "🔥 GÜÇLÜ TETİK"
    elif puan >= 60:
        seviye = "🟢 ERKEN TETİK"
    elif puan >= 40:
        seviye = "🟡 ZAYIF TETİK"
    else:
        seviye = "⏳ TETİK YOK"

    if sahte_kirilim and puan < 80:
        mesaj = f"❌ SAHTE KIRILIM RİSKİ · {seviye} ({puan}/100)"
        detay.insert(0, "⚠️ Mum direnci test etti fakat altında kapandı ve üst fitil bıraktı")
    else:
        mesaj = f"{seviye} ({puan}/100)"

    return {
        "puan": puan,
        "seviye": seviye,
        "mesaj": mesaj,
        "detay": detay,
        "direnc": direnc,
        "hacim_orani": hacim_orani,
        "rsi": rsi,
        "mum_kalitesi": kapanis_konumu,
        "sahte_kirilim": sahte_kirilim,
    }


def giris_motoru_hesapla(intraday_5dk, uzun_vade_trend):
    """5 dk, 15 dk ve 1 saat verisini birleştirerek 0-100 Giriş Kalitesi üretir.

    5 dakika kısa vadeli hareketin başladığını, 15 dakika hareketin genişleyip
    genişlemediğini, 1 saat ise girişin daha büyük zaman dilimiyle uyumunu ölçer.
    Kapanmamış mumlar her zaman diliminde tetik_puani_hesapla tarafından dışlanır.
    """
    uygulanmaz = {
        "puan": 0, "seviye": "— UYGULANMAZ",
        "mesaj": "— Giriş motoru değerlendirilmez: alım yönlü sinyal yok",
        "detay": ["Giriş kalitesi yalnızca alım yönlü ön sinyallerde hesaplanır."],
        "zaman_dilimleri": {}, "asama": "UYGULANMAZ",
        "direnc": None, "hacim_orani": 0.0, "rsi": None,
        "mum_kalitesi": 0.0, "sahte_kirilim": False,
    }
    if intraday_5dk is None or intraday_5dk.empty:
        sonuc = uygulanmaz.copy()
        sonuc.update({"seviye":"⏳ VERİ BEKLENİYOR", "mesaj":"⏳ Giriş motoru için gün içi veri bulunamadı", "asama":"VERİ YOK"})
        return sonuc

    zamanlar = {
        "5 Dk": intraday_5dk,
        "15 Dk": _resample_ohlcv(intraday_5dk, "15min"),
        "1 Saat": _resample_ohlcv(intraday_5dk, "60min"),
    }
    agirliklar = {"5 Dk": 0.40, "15 Dk": 0.35, "1 Saat": 0.25}
    sonuclar = {}
    kullanilan_agirlik = 0.0
    agirlikli_toplam = 0.0

    for ad, veri in zamanlar.items():
        sonuc = tetik_puani_hesapla(veri, uzun_vade_trend)
        yeterli = veri is not None and not veri.empty and len(veri) >= 24 and sonuc.get("direnc") is not None
        sonuc["yeterli_veri"] = bool(yeterli)
        sonuclar[ad] = sonuc
        if yeterli:
            w = agirliklar[ad]
            kullanilan_agirlik += w
            agirlikli_toplam += float(sonuc.get("puan", 0)) * w

    if kullanilan_agirlik <= 0:
        sonuc = uygulanmaz.copy()
        sonuc.update({"seviye":"⏳ VERİ BEKLENİYOR", "mesaj":"⏳ Giriş motoru için yeterli kapanmış mum yok", "zaman_dilimleri":sonuclar, "asama":"VERİ YOK"})
        return sonuc

    puan = int(round(agirlikli_toplam / kullanilan_agirlik))
    p5 = int(sonuclar["5 Dk"].get("puan", 0))
    p15 = int(sonuclar["15 Dk"].get("puan", 0))
    p60 = int(sonuclar["1 Saat"].get("puan", 0))

    # Üst zaman dilimleri kısa vadeli hareketi teyit ediyorsa küçük uyum bonusu.
    if sonuclar["15 Dk"].get("yeterli_veri") and sonuclar["1 Saat"].get("yeterli_veri"):
        if p15 >= 60 and p60 >= 60:
            puan += 5
        elif p5 >= 75 and p15 < 40 and p60 < 40:
            puan -= 12

    sahte = any(bool(v.get("sahte_kirilim", False)) for v in sonuclar.values())
    if sahte:
        puan -= 8
    puan = int(max(0, min(100, puan)))

    if puan >= 85 and p15 >= 70 and p60 >= 60:
        seviye, asama = "🔵 TEYİT EDİLDİ", "TEYİT EDİLDİ"
    elif puan >= 75:
        seviye, asama = "🔥 GÜÇLÜ GİRİŞ", "GÜÇLÜ"
    elif puan >= 55:
        seviye, asama = "🟢 ERKEN GİRİŞ", "ERKEN"
    elif puan >= 35:
        seviye, asama = "🟡 HAZIRLANIYOR", "HAZIRLANIYOR"
    else:
        seviye, asama = "⏳ GİRİŞ UYGUN DEĞİL", "YOK"

    if p5 >= 75 and p15 < 45 and p60 < 45:
        seviye = "⚠️ KISA VADELİ TEPKİ RİSKİ"
        asama = "UYUMSUZ"

    detay = [
        f"⏱️ 5 dk zamanlama puanı: {p5}/100",
        f"🕒 15 dk teyit puanı: {p15}/100",
        f"🧭 1 saat trend teyidi: {p60}/100",
    ]
    if p15 >= 60 and p60 >= 60:
        detay.append("✅ Üst zaman dilimleri kısa vadeli hareketi destekliyor")
    elif p5 >= 75 and p15 < 40 and p60 < 40:
        detay.append("⚠️ 5 dk güçlü fakat 15 dk ve 1 saat uyumsuz; kısa tepki olabilir")
    else:
        detay.append("🟡 Zaman dilimleri arasında tam uyum henüz oluşmadı")
    if sahte:
        detay.append("⚠️ En az bir zaman diliminde sahte kırılım riski tespit edildi")

    mesaj = f"{seviye} · Giriş Kalitesi {puan}/100 (5D:{p5} · 15D:{p15} · 1S:{p60})"
    referans = sonuclar.get("5 Dk", {})
    return {
        "puan": puan, "seviye": seviye, "mesaj": mesaj, "detay": detay,
        "zaman_dilimleri": sonuclar, "asama": asama,
        "direnc": referans.get("direnc"),
        "hacim_orani": float(referans.get("hacim_orani", 0.0) or 0.0),
        "rsi": referans.get("rsi"),
        "mum_kalitesi": float(referans.get("mum_kalitesi", 0.0) or 0.0),
        "sahte_kirilim": sahte,
    }


# --- GELİŞMİŞ TEKNİK / DOĞRULAMA MOTORU ---
def _rsi_serisi(close, period=14):
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1/period, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1/period, adjust=False).mean()
    return 100 - (100 / (1 + gain / (loss + 1e-9)))


def adx_hesapla(df, period=14):
    high, low, close = df['High'], df['Low'], df['Close']
    plus_dm = high.diff().where((high.diff() > -low.diff()) & (high.diff() > 0), 0.0)
    minus_dm = (-low.diff()).where((-low.diff() > high.diff()) & (-low.diff() > 0), 0.0)
    tr = pd.concat([(high-low), (high-close.shift()).abs(), (low-close.shift()).abs()], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1/period, adjust=False).mean()
    plus_di = 100 * plus_dm.ewm(alpha=1/period, adjust=False).mean() / (atr + 1e-9)
    minus_di = 100 * minus_dm.ewm(alpha=1/period, adjust=False).mean() / (atr + 1e-9)
    dx = 100 * (plus_di-minus_di).abs() / (plus_di+minus_di+1e-9)
    adx = dx.ewm(alpha=1/period, adjust=False).mean()
    return float(adx.iloc[-1]), float(plus_di.iloc[-1]), float(minus_di.iloc[-1])


def cmf_hesapla(df, period=20):
    denom = (df['High']-df['Low']).replace(0, np.nan)
    mfm = ((df['Close']-df['Low'])-(df['High']-df['Close'])) / denom
    mfv = mfm.fillna(0) * df['Volume'].fillna(0)
    cmf = mfv.rolling(period).sum() / (df['Volume'].rolling(period).sum()+1e-9)
    ad_line = mfv.cumsum()
    return float(cmf.iloc[-1]) if pd.notna(cmf.iloc[-1]) else 0.0, float(ad_line.iloc[-1])


def supertrend_hesapla(df, period=10, multiplier=3.0):
    high, low, close = df['High'], df['Low'], df['Close']
    tr = pd.concat([(high-low), (high-close.shift()).abs(), (low-close.shift()).abs()], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1/period, adjust=False).mean()
    hl2 = (high+low)/2
    upper = hl2 + multiplier*atr
    lower = hl2 - multiplier*atr
    final_upper, final_lower = upper.copy(), lower.copy()
    trend = pd.Series(1, index=df.index, dtype=int)
    for i in range(1, len(df)):
        final_upper.iloc[i] = upper.iloc[i] if (upper.iloc[i] < final_upper.iloc[i-1] or close.iloc[i-1] > final_upper.iloc[i-1]) else final_upper.iloc[i-1]
        final_lower.iloc[i] = lower.iloc[i] if (lower.iloc[i] > final_lower.iloc[i-1] or close.iloc[i-1] < final_lower.iloc[i-1]) else final_lower.iloc[i-1]
        if close.iloc[i] > final_upper.iloc[i-1]: trend.iloc[i] = 1
        elif close.iloc[i] < final_lower.iloc[i-1]: trend.iloc[i] = -1
        else: trend.iloc[i] = trend.iloc[i-1]
    line = final_lower if trend.iloc[-1] == 1 else final_upper
    return int(trend.iloc[-1]), float(line.iloc[-1])


def seans_vwap_hesapla(intraday):
    if intraday is None or intraday.empty or not {'High','Low','Close','Volume'}.issubset(intraday.columns):
        return np.nan
    d = intraday.dropna(subset=['Close']).copy()
    if d.empty: return np.nan
    d = d[d.index.date == d.index[-1].date()]
    tp = (d['High']+d['Low']+d['Close'])/3
    vol = d['Volume'].fillna(0)
    return float((tp*vol).sum()/(vol.sum()+1e-9))


def _resample_ohlcv(df, rule):
    """Normal seans başlangıcına hizalı OHLCV üretir.

    Özellikle ABD hisselerinde seans 09:30'da başladığı için varsayılan saat-başı
    resample ilk 1 saatlik mumu 09:30-10:00 gibi eksik oluşturabiliyordu.
    Zaman dilimine göre seans açılışını doğru ankora çeviriyoruz.
    """
    if df is None or df.empty:
        return pd.DataFrame()
    x = df.copy().sort_index()
    try:
        td = pd.Timedelta(rule)
        kural_dk = max(1, int(td.total_seconds() // 60))
        tz_str = str(getattr(x.index, 'tz', '') or '')
        seans_acilis_dk = 570 if 'New_York' in tz_str else 600 if 'Istanbul' in tz_str else 0
        offset = pd.Timedelta(minutes=(seans_acilis_dk % kural_dk)) if seans_acilis_dk else pd.Timedelta(0)
        return (x.resample(rule, origin='start_day', offset=offset)
                 .agg({'Open':'first','High':'max','Low':'min','Close':'last','Volume':'sum'})
                 .dropna(subset=['Close']))
    except Exception:
        return (x.resample(rule)
                 .agg({'Open':'first','High':'max','Low':'min','Close':'last','Volume':'sum'})
                 .dropna(subset=['Close']))


def _zaman_dilimi_karari(df):
    if df is None or len(df) < 30: return {'yon':'VERİ YOK','puan':0}
    c=df['Close']
    ema9=c.ewm(span=9,adjust=False).mean().iloc[-1]
    ema21=c.ewm(span=21,adjust=False).mean().iloc[-1]
    rsi=float(_rsi_serisi(c).iloc[-1])
    macd=c.ewm(span=12,adjust=False).mean()-c.ewm(span=26,adjust=False).mean()
    ms=macd.ewm(span=9,adjust=False).mean()
    puan=0
    puan += 1 if c.iloc[-1]>ema21 else -1
    puan += 1 if ema9>ema21 else -1
    puan += 1 if macd.iloc[-1]>ms.iloc[-1] else -1
    puan += 1 if 50<=rsi<=70 else (-1 if rsi<40 or rsi>75 else 0)
    yon='AL' if puan>=2 else 'SAT' if puan<=-2 else 'NÖTR'
    return {'yon':yon,'puan':puan,'rsi':rsi}


def coklu_zaman_dilimi_analizi(intraday, daily):
    """MTF uyumunu yalnızca tamamlanmış gün içi mumlarla hesaplar.

    Giriş motoru kapanmamış mumu zaten dışlıyordu; MTF katmanında aynı koruma
    yoktu. Bu nedenle yarım oluşmuş 5/15/60/240 dk mumlar merkezi karar puanını
    geçici olarak oynatabiliyordu.
    """
    sonuclar={}
    if intraday is not None and not intraday.empty:
        kapali_5 = _yalnizca_kapali_mumlar(intraday)
        sonuclar['5Dk']=_zaman_dilimi_karari(kapali_5)
        for ad, kural in [('15Dk','15min'), ('1S','60min'), ('4S','240min')]:
            yeniden = _resample_ohlcv(kapali_5, kural)
            yeniden = _yalnizca_kapali_mumlar(yeniden, varsayilan_dakika=int(pd.Timedelta(kural).total_seconds() // 60))
            sonuclar[ad]=_zaman_dilimi_karari(yeniden)
    sonuclar['Günlük']=_zaman_dilimi_karari(daily)
    gecerli=[v for v in sonuclar.values() if v.get('yon')!='VERİ YOK']
    net=sum(v.get('puan',0) for v in gecerli)
    maxp=max(len(gecerli)*4,1)
    uyum=round(50+50*net/maxp)
    uyum=int(min(100,max(0,uyum)))
    return sonuclar, uyum


def volatilite_rejimi(fiyat, atr, hv20):
    atrp=(atr/fiyat*100) if fiyat>0 else 0
    if atrp>=5 or hv20>=0.75: return 'PANİK / ÇOK YÜKSEK'
    if atrp>=3 or hv20>=0.45: return 'YÜKSEK'
    if atrp>=1.5 or hv20>=0.25: return 'NORMAL'
    return 'SAKİN'


def sinyal_guven_skoru(panel, temel_skor):
    puan=50.0
    puan += min(12,max(-12,(temel_skor-50)*0.35))
    puan += 8 if panel.get('adx',0)>=25 and panel.get('plus_di',0)>panel.get('minus_di',0) else (-5 if panel.get('adx',0)<18 else 0)
    puan += 7 if panel.get('cmf',0)>0.05 else (-7 if panel.get('cmf',0)<-0.05 else 0)
    puan += 6 if panel.get('supertrend',0)==1 else -6
    puan += 5 if panel.get('fiyat',0)>panel.get('vwap',float('inf')) else (-3 if np.isfinite(panel.get('vwap',np.nan)) else 0)
    puan += (panel.get('mtf_uyum',50)-50)*0.20
    sektorel_fark_v = panel.get('sektorel_fark', np.nan)
    if pd.notna(sektorel_fark_v) and np.isfinite(float(sektorel_fark_v)):
        puan += 4 if float(sektorel_fark_v) > 0 else -3
    puan += 3 if panel.get('risk_odul',0)>=2 else (-3 if panel.get('risk_odul',0)<1.2 else 0)
    return int(round(min(95,max(20,puan))))


def _safe_float(value, default=0.0):
    """Karar motorunu NaN/None/string kaynaklı tek-varlık hatalarına karşı korur."""
    try:
        x = float(value)
        return x if np.isfinite(x) else float(default)
    except (TypeError, ValueError, OverflowError):
        return float(default)


def _safe_int(value, default=0):
    try:
        x = float(value)
        return int(round(x)) if np.isfinite(x) else int(default)
    except (TypeError, ValueError, OverflowError):
        return int(default)


def merkezi_karar_motoru(panel):
    """IZFIN'in tek karar beyni.

    Profil, hibrit skor, giriş kalitesi, algoritma güveni, MTF uyumu,
    trend/momentum/para akışı ve risk verilerini birlikte değerlendirir.
    Görsel paneller karar üretmez; yalnızca bu fonksiyonun sonucunu gösterir.
    """
    profil = str(panel.get('profil', panel.get('on_sinyal', 'NÖTR')))
    profil_u = profil.upper()
    skor = _safe_int(panel.get('nihai_skor', panel.get('cezali_skor', panel.get('skor', 50))), 50)
    giris = _safe_int(panel.get('giris_puani', panel.get('tetik_puani', 0)), 0)
    guven = _safe_int(panel.get('guven_skoru', 50), 50)
    mtf = _safe_int(panel.get('mtf_uyum', 50), 50)
    risk = str(panel.get('risk_seviyesi', 'ORTA') or 'ORTA').upper()
    vol_rejimi = str(panel.get('volatilite_rejimi', '') or '').upper()

    fiyat = _safe_float(panel.get('fiyat', 0), 0)
    ema9 = _safe_float(panel.get('ema9', fiyat), fiyat)
    ema21 = _safe_float(panel.get('ema21', fiyat), fiyat)
    ema50 = _safe_float(panel.get('ema50', fiyat), fiyat)
    sma200 = _safe_float(panel.get('sma200', fiyat), fiyat)
    rsi = _safe_float(panel.get('rsi', 50), 50)
    mfi = _safe_float(panel.get('mfi', 50), 50)
    macd = _safe_float(panel.get('macd', 0), 0)
    macd_signal = _safe_float(panel.get('macd_signal', 0), 0)
    cmf = _safe_float(panel.get('cmf', 0), 0)
    adx = _safe_float(panel.get('adx', 0), 0)
    plus_di = _safe_float(panel.get('plus_di', 0), 0)
    minus_di = _safe_float(panel.get('minus_di', 0), 0)
    supertrend = _safe_int(panel.get('supertrend', 0), 0)
    bb_raw = panel.get('bb_ust', None)
    bb_ust = _safe_float(bb_raw, float('inf')) if bb_raw is not None else float('inf')
    risk_odul = _safe_float(panel.get('risk_odul', 0), 0)
    sahte_kirilim = bool(panel.get('tetik_sahte_kirilim', False))

    trend_ana = fiyat > sma200 and fiyat > ema50
    trend_kisa = ema9 > ema21
    trend_guclu = trend_ana and trend_kisa and supertrend == 1
    momentum_pozitif = macd > macd_signal and plus_di >= minus_di
    para_akisi_pozitif = cmf >= 0
    asiri_isinmis = rsi >= 70 and np.isfinite(bb_ust) and fiyat >= bb_ust * 0.995
    momentum_bozuluyor = macd <= macd_signal or fiyat < ema9 or cmf < -0.03 or mfi < 45
    yuksek_risk = risk in {'YÜKSEK', 'ÇOK YÜKSEK', 'PANİK / ÇOK YÜKSEK'} or 'PANİK' in vol_rejimi
    alim_profili = any(x in profil_u for x in ['ALIM', 'KIRILIM', 'ADAY'])
    tepki_profili = 'HACİMLİ TEPKİ' in profil_u or 'KURTULUŞ' in profil_u

    olumlu, olumsuz = [], []
    if trend_ana: olumlu.append('ana trend yukarı')
    else: olumsuz.append('ana trend teyidi yok')
    if trend_kisa: olumlu.append('EMA9/EMA21 kısa trend uyumlu')
    else: olumsuz.append('kısa trend zayıf')
    if adx >= 25: olumlu.append('trend gücü yüksek')
    elif adx < 18: olumsuz.append('trend gücü sınırlı')
    if cmf > 0.05: olumlu.append('CMF para girişini destekliyor')
    elif cmf < -0.05: olumsuz.append('CMF para akışı zayıf')
    if supertrend == 1: olumlu.append('SuperTrend yukarı')
    else: olumsuz.append('SuperTrend aşağı')
    if mtf >= 70: olumlu.append(f'zaman dilimleri güçlü uyumlu (%{mtf})')
    elif mtf >= 60: olumlu.append(f'zaman dilimleri uyumlu (%{mtf})')
    elif mtf <= 40: olumsuz.append(f'zaman dilimleri çatışıyor (%{mtf})')
    if giris >= 80: olumlu.append(f'giriş bölgesi güçlü ({giris}/100)')
    elif giris >= 55: olumlu.append(f'giriş kalitesi gelişiyor ({giris}/100)')
    elif alim_profili: olumsuz.append(f'giriş teyidi yetersiz ({giris}/100)')
    if guven >= 75: olumlu.append(f'algoritma güveni yüksek (%{guven})')
    elif guven < 65: olumsuz.append(f'algoritma güveni sınırlı (%{guven})')
    if sahte_kirilim: olumsuz.append('sahte kırılım riski var')
    if yuksek_risk: olumsuz.append(f'risk seviyesi {risk.lower()}')
    if risk_odul and risk_odul < 1.2: olumsuz.append('risk/ödül zayıf')

    if (not trend_ana and skor < 45) or (supertrend == -1 and mtf <= 40 and guven < 55):
        karar, aksiyon = 'SAT / KAÇIN 🔴', 'SAT_KACIN'
    elif asiri_isinmis and momentum_bozuluyor:
        karar, aksiyon = 'KÂR AL / RİSK AZALT 🟠', 'KAR_AL'
    elif 'MOMENTUM AŞIRI ISINDI' in profil_u and (rsi >= 68 or yuksek_risk):
        karar, aksiyon = 'KÂR KORU / YENİ GİRİŞ BEKLE 🟠', 'KAR_KORU'
    elif (alim_profili and trend_guclu and momentum_pozitif and para_akisi_pozitif
          and guven >= 80 and giris >= 80 and mtf >= 70 and not yuksek_risk
          and not sahte_kirilim and not asiri_isinmis):
        karar, aksiyon = 'GÜÇLÜ AL 🚀', 'GUCLU_AL'
    elif (alim_profili and trend_ana and supertrend == 1 and guven >= 70 and giris >= 65
          and mtf >= 60 and cmf >= -0.03 and not yuksek_risk and not sahte_kirilim and not asiri_isinmis):
        karar, aksiyon = 'AL 🟢', 'AL'
    elif (alim_profili and trend_ana and guven >= 62 and giris >= 55 and mtf >= 55
          and not yuksek_risk and cmf >= -0.05 and not sahte_kirilim and not asiri_isinmis):
        karar, aksiyon = 'ERKEN AL 🟢', 'ERKEN_AL'
    elif alim_profili:
        karar, aksiyon = 'TEYİT BEKLE 🟡', 'TEYIT_BEKLE'
    elif tepki_profili and guven >= 45:
        karar, aksiyon = 'İZLE / TEYİT BEKLE 🟡', 'IZLE'
    elif guven < 40 or (supertrend == -1 and not trend_ana):
        karar, aksiyon = 'RİSKTEN KAÇIN 🔴', 'RISK_KACIN'
    else:
        karar, aksiyon = 'İZLE / NÖTR ⚪', 'IZLE'

    nedenler = []
    if aksiyon in {'GUCLU_AL', 'AL', 'ERKEN_AL'}:
        nedenler = olumlu[:4]
        if olumsuz:
            nedenler.append('Sınırlayıcı: ' + olumsuz[0])
    elif aksiyon in {'TEYIT_BEKLE', 'IZLE'}:
        if olumlu:
            nedenler.append('Olumlu: ' + ', '.join(olumlu[:2]))
        if olumsuz:
            nedenler.append('Bekleme nedeni: ' + ', '.join(olumsuz[:3]))
    else:
        nedenler = olumsuz[:4] or ['risk/getiri yapısı yeni pozisyon için yeterli değil']

    ozet = ' · '.join(nedenler) if nedenler else 'Karar, mevcut teknik verilerin ortak değerlendirmesinden üretildi.'
    return {
        'karar': karar, 'aksiyon': aksiyon, 'profil': profil,
        'guven': guven, 'risk': risk, 'mtf_uyum': mtf,
        'giris_puani': giris, 'hibrit_skor': skor,
        'olumlu': olumlu, 'olumsuz': olumsuz, 'ozet': ozet,
    }


def karar_motoru_ozeti(panel):
    """Şeffaf panel ikinci bir karar üretmez; merkezi kararın aynısını döndürür."""
    karar = panel.get('merkezi_karar') if isinstance(panel, dict) else None
    if isinstance(karar, dict) and karar.get('karar'):
        return karar
    return merkezi_karar_motoru(panel or {})


def _backtest_supertrend_serisi(df, period=10, multiplier=3.0):
    """Canlı SuperTrend mantığının tüm geçmiş için nedensel (causal) seri karşılığı."""
    high = pd.to_numeric(df['High'], errors='coerce')
    low = pd.to_numeric(df['Low'], errors='coerce')
    close = pd.to_numeric(df['Close'], errors='coerce')
    tr = pd.concat([(high-low), (high-close.shift()).abs(), (low-close.shift()).abs()], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1/period, adjust=False).mean()
    hl2 = (high+low)/2
    upper = hl2 + multiplier*atr
    lower = hl2 - multiplier*atr
    final_upper, final_lower = upper.copy(), lower.copy()
    trend = pd.Series(1, index=df.index, dtype=int)
    for i in range(1, len(df)):
        final_upper.iloc[i] = upper.iloc[i] if (upper.iloc[i] < final_upper.iloc[i-1] or close.iloc[i-1] > final_upper.iloc[i-1]) else final_upper.iloc[i-1]
        final_lower.iloc[i] = lower.iloc[i] if (lower.iloc[i] > final_lower.iloc[i-1] or close.iloc[i-1] < final_lower.iloc[i-1]) else final_lower.iloc[i-1]
        if close.iloc[i] > final_upper.iloc[i-1]:
            trend.iloc[i] = 1
        elif close.iloc[i] < final_lower.iloc[i-1]:
            trend.iloc[i] = -1
        else:
            trend.iloc[i] = trend.iloc[i-1]
    return trend


def _backtest_adx_serileri(df, period=14):
    """ADX/+DI/-DI değerlerini tüm geçmiş için tek seferde hesaplar."""
    high = pd.to_numeric(df['High'], errors='coerce')
    low = pd.to_numeric(df['Low'], errors='coerce')
    close = pd.to_numeric(df['Close'], errors='coerce')
    up = high.diff()
    down = -low.diff()
    plus_dm = up.where((up > down) & (up > 0), 0.0)
    minus_dm = down.where((down > up) & (down > 0), 0.0)
    tr = pd.concat([(high-low), (high-close.shift()).abs(), (low-close.shift()).abs()], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1/period, adjust=False).mean()
    plus_di = 100 * plus_dm.ewm(alpha=1/period, adjust=False).mean() / (atr + 1e-9)
    minus_di = 100 * minus_dm.ewm(alpha=1/period, adjust=False).mean() / (atr + 1e-9)
    dx = 100 * (plus_di-minus_di).abs() / (plus_di+minus_di+1e-9)
    adx = dx.ewm(alpha=1/period, adjust=False).mean()
    return adx, plus_di, minus_di


def _backtest_daily_mtf_proxy(i, c, ema9, ema21, ema50, sma200, macd, macd_signal, rsi, adx, plus_di, minus_di):
    """Intraday geçmişi olmayan uzun dönem test için yalnızca günlük veriden zaman-ölçeği uyumu.

    Bu değer canlı 5dk/15dk/1s MTF'nin yerine geçmiş intraday veri uydurmaz; günlük kısa/orta/uzun
    trend katmanlarının aynı yöne bakıp bakmadığını 0-100 ölçeğine taşır.
    """
    if i < 200:
        return 50
    puanlar = []
    # Kısa günlük yapı
    p = 0
    p += 1 if c.iloc[i] > ema21.iloc[i] else -1
    p += 1 if ema9.iloc[i] > ema21.iloc[i] else -1
    p += 1 if macd.iloc[i] > macd_signal.iloc[i] else -1
    rv = float(rsi.iloc[i]) if pd.notna(rsi.iloc[i]) else 50.0
    p += 1 if 50 <= rv <= 70 else (-1 if rv < 40 or rv > 75 else 0)
    puanlar.append(p)
    # Orta vadeli günlük yapı
    p = 0
    p += 1 if c.iloc[i] > ema50.iloc[i] else -1
    p += 1 if ema21.iloc[i] > ema50.iloc[i] else -1
    p += 1 if macd.iloc[i] > macd_signal.iloc[i] else -1
    p += 1 if (adx.iloc[i] >= 20 and plus_di.iloc[i] >= minus_di.iloc[i]) else -1
    puanlar.append(p)
    # Uzun vadeli günlük yapı
    p = 0
    p += 1 if c.iloc[i] > sma200.iloc[i] else -1
    p += 1 if ema50.iloc[i] > sma200.iloc[i] else -1
    p += 1 if i >= 20 and c.iloc[i] > c.iloc[i-20] else -1
    p += 1 if plus_di.iloc[i] >= minus_di.iloc[i] else -1
    puanlar.append(p)
    net = sum(puanlar)
    return int(max(0, min(100, round(50 + 50 * net / 12))))


def _backtest_giris_proxy(on_sinyal, skor, hacim_oran, ema9_gt_ema21, macd_gt_signal,
                          adx, cmf, supertrend, rsi, mfi):
    """Uzun dönem günlük testte intraday giriş puanı yerine kullanılan açıkça etiketli proxy.

    Amaç 5dk veri varmış gibi davranmak değil; günlük adayın ne kadar olgun olduğunu aynı 0-100
    ölçeğinde yaklaşıklaştırmaktır. Canlı uygulamadaki gerçek giriş motorunun yerine geçmez.
    """
    s = str(on_sinyal).upper()
    if not any(x in s for x in ['ALIM', 'KIRILIM', 'ADAY']):
        return 0
    if 'KIRILIM' in s:
        puan = 60
    elif 'KUSURSUZ ALIM' in s:
        puan = 55
    elif 'KADEMELİ ALIM' in s:
        puan = 50
    else:
        puan = 45
    if skor >= 70: puan += 8
    if skor >= 80: puan += 4
    if hacim_oran >= 120: puan += 7
    if hacim_oran >= 150: puan += 3
    if ema9_gt_ema21: puan += 6
    if macd_gt_signal: puan += 6
    if adx >= 25: puan += 6
    elif adx < 18: puan -= 5
    if cmf > 0.05: puan += 5
    elif cmf < -0.05: puan -= 5
    if supertrend == 1: puan += 5
    else: puan -= 5
    if 35 <= rsi <= 68: puan += 4
    if mfi < 30: puan -= 3
    return int(max(0, min(100, puan)))


@st.cache_data(ttl=3600, show_spinner=False)
def basit_backtest(ticker, period='5y'):
    """IZFIN Daily Core geçmiş doğrulaması.

    Her geçmiş günde yalnızca o gün ve öncesindeki bilgi kullanılarak canlı sistemin günlük
    çekirdeğine mümkün olduğunca aynı analiz zinciri uygulanır: hibrit skor, ADX/DI, CMF,
    SuperTrend, volatilite/risk, teknik profil, algoritma güveni ve merkezi karar motoru.

    Uzun dönem 5dk/15dk/1s geçmişi bulunmadığı için canlı intraday Giriş Motoru ve seans VWAP'ı
    birebir geriye yürütülmez. Bunların yerine geçmiş veri uydurulmaz; günlük ölçekten türetilen
    'Daily MTF' ve 'Giriş Proxy' açıkça ayrı alanlar olarak kullanılır.
    """
    try:
        df = yf.download(
            ticker, period=period, progress=False, auto_adjust=True,
            threads=False, timeout=10,
        )
        df = _normalize_yf_columns(df).dropna(subset=['Close','High','Low','Volume']).copy()
    except Exception as e:
        izfin_hata_logla('backtest_veri', e, ticker)
        return pd.DataFrame(), {}

    if len(df) < 260:
        return pd.DataFrame(), {}

    c = pd.to_numeric(df['Close'], errors='coerce')
    h = pd.to_numeric(df['High'], errors='coerce')
    l = pd.to_numeric(df['Low'], errors='coerce')
    v = pd.to_numeric(df['Volume'], errors='coerce').fillna(0)

    ema9 = c.ewm(span=9, adjust=False).mean()
    ema21 = c.ewm(span=21, adjust=False).mean()
    ema50 = c.ewm(span=50, adjust=False).mean()
    sma200 = c.rolling(200).mean()
    rsi_ser = _rsi_serisi(c)
    macd = c.ewm(span=12, adjust=False).mean() - c.ewm(span=26, adjust=False).mean()
    macd_signal = macd.ewm(span=9, adjust=False).mean()
    bb_mid = c.rolling(20).mean()
    bb_std = c.rolling(20).std()
    bb_alt = bb_mid - 2 * bb_std
    bb_ust = bb_mid + 2 * bb_std
    hacim_sma20 = v.rolling(20, min_periods=5).mean()
    hacim_oran_ser = v / (hacim_sma20 + 1e-9) * 100

    typical = (h + l + c) / 3
    raw_flow = typical * v
    pos_flow = pd.Series(np.where(typical > typical.shift(1), raw_flow, 0.0), index=df.index)
    neg_flow = pd.Series(np.where(typical < typical.shift(1), raw_flow, 0.0), index=df.index)
    mfi_ser = 100 - (100 / (1 + pos_flow.rolling(14).sum() / (neg_flow.rolling(14).sum() + 1e-5)))

    obv = pd.Series(np.where(c > c.shift(1), v, np.where(c < c.shift(1), -v, 0.0)), index=df.index).cumsum()
    obv_ema = obv.ewm(span=20, adjust=False).mean()

    adx_ser, plus_di_ser, minus_di_ser = _backtest_adx_serileri(df)
    denom = (h-l).replace(0, np.nan)
    mfm = ((c-l)-(h-c)) / denom
    mfv = mfm.fillna(0) * v
    cmf_ser = mfv.rolling(20).sum() / (v.rolling(20).sum() + 1e-9)
    supertrend_ser = _backtest_supertrend_serisi(df)

    prev_close = c.shift(1)
    tr = pd.concat([(h-l).abs(), (h-prev_close).abs(), (l-prev_close).abs()], axis=1).max(axis=1)
    atr14 = tr.rolling(14).mean()
    log_ret = np.log(c / c.shift(1)).replace([np.inf, -np.inf], np.nan)
    hv20_ser = log_ret.rolling(20).std(ddof=1) * np.sqrt(252)

    rows = []
    sonraki_yeni_giris = 200
    is_bist = str(ticker).upper().endswith('.IS')

    # İlk 200 gün gösterge olgunlaşması içindir; son 5 gün sabit ufuk için korunur.
    for i in range(200, len(df) - 5):
        if i < sonraki_yeni_giris:
            continue
        if any(pd.isna(x) for x in [sma200.iloc[i], ema50.iloc[i], bb_mid.iloc[i], bb_ust.iloc[i], bb_alt.iloc[i], atr14.iloc[i]]):
            continue

        fiyat = float(c.iloc[i])
        onceki = float(c.iloc[i-1]) if i > 0 else fiyat
        gunluk_degisim = ((fiyat / onceki) - 1) * 100 if onceki > 0 else 0.0
        hacim_oran = float(hacim_oran_ser.iloc[i]) if pd.notna(hacim_oran_ser.iloc[i]) else 100.0
        rsi = float(rsi_ser.iloc[i]) if pd.notna(rsi_ser.iloc[i]) else 50.0
        mfi = float(mfi_ser.iloc[i]) if pd.notna(mfi_ser.iloc[i]) else 50.0
        adx = float(adx_ser.iloc[i]) if pd.notna(adx_ser.iloc[i]) else 0.0
        plus_di = float(plus_di_ser.iloc[i]) if pd.notna(plus_di_ser.iloc[i]) else 0.0
        minus_di = float(minus_di_ser.iloc[i]) if pd.notna(minus_di_ser.iloc[i]) else 0.0
        cmf = float(cmf_ser.iloc[i]) if pd.notna(cmf_ser.iloc[i]) else 0.0
        supertrend = int(supertrend_ser.iloc[i])
        atr = float(atr14.iloc[i])
        hv20 = float(hv20_ser.iloc[i]) if pd.notna(hv20_ser.iloc[i]) and hv20_ser.iloc[i] > 0 else float((atr/fiyat)*np.sqrt(252))
        uzun_vade_trend = fiyat > float(sma200.iloc[i])
        hacim_patlamasi = hacim_oran >= 130 and gunluk_degisim >= 4.0
        ort_ciro = float(hacim_sma20.iloc[i] * fiyat) if pd.notna(hacim_sma20.iloc[i]) else 0.0
        is_sig_tahta = ort_ciro < (50_000_000 if is_bist else 5_000_000)

        # Canlı hibrit skorun aynı günlük bileşenleri.
        eski_skor = 50
        eski_skor += 15 if uzun_vade_trend else (-5 if hacim_patlamasi else -25)
        eski_skor += 10 if fiyat > float(ema50.iloc[i]) else -15
        eski_skor += 15 if (hacim_oran >= 100 and obv.iloc[i] > obv_ema.iloc[i]) else -20
        if 35 <= rsi <= 55:
            eski_skor += 10
        elif rsi > 70:
            eski_skor -= 15
        eski_skor += 10 if macd.iloc[i] > macd_signal.iloc[i] else -10
        if fiyat <= float(bb_mid.iloc[i]):
            eski_skor += 10
        elif fiyat >= float(bb_ust.iloc[i]) and rsi >= 65:
            eski_skor -= 15
        if is_sig_tahta:
            eski_skor -= 20
        eski_skor = int(max(0, min(100, eski_skor)))

        mtf_uyum = _backtest_daily_mtf_proxy(
            i, c, ema9, ema21, ema50, sma200, macd, macd_signal, rsi_ser,
            adx_ser, plus_di_ser, minus_di_ser,
        )
        bonus = ceza = 0
        if adx >= 25 and plus_di > minus_di: bonus += 6
        elif adx < 18: ceza += 4
        if cmf > 0.05: bonus += 5
        elif cmf < -0.05: ceza += 5
        if supertrend == 1: bonus += 4
        else: ceza += 4
        mtf_etki = int(round((mtf_uyum - 50) * 0.10))
        if mtf_etki > 0: bonus += mtf_etki
        elif mtf_etki < 0: ceza += abs(mtf_etki)
        # Seans VWAP ve geçmiş tarihli sektör referansı uzun dönem veri setinde yok:
        # bu iki alan nötrdür; veri uydurulmaz.
        bonus = min(bonus, 15)
        ceza = min(ceza, 15)
        skor = int(max(0, min(100, eski_skor + bonus - ceza)))

        hist = df.iloc[:i+1].copy()
        gecmis = df.iloc[:i] if i > 0 else hist
        swing_high = float(pd.to_numeric(gecmis['High'], errors='coerce').tail(50).max())
        swing_low = float(pd.to_numeric(gecmis['Low'], errors='coerce').tail(50).min())
        seviyeler = teknik_seviyeler_hesapla(
            hist, fiyat, atr, float(ema50.iloc[i]), float(bb_alt.iloc[i]),
            float(bb_mid.iloc[i]), float(bb_ust.iloc[i]), hv20,
        )
        karma_destek = float(seviyeler['s1'])
        tp1, tp2, tp3 = float(seviyeler['tp1']), float(seviyeler['tp2']), float(seviyeler['tp3'])
        chandelier = float(pd.to_numeric(gecmis['High'], errors='coerce').tail(22).max()) - atr*3
        stop_adaylari = [x for x in [chandelier, fiyat-atr*1.5, karma_destek-atr*0.25] if pd.notna(x) and x < fiyat]
        stop = max(stop_adaylari, default=fiyat-atr*1.5)
        risk_yuzde = (fiyat-stop) / max(fiyat, 1e-9) * 100
        risk_seviyesi = 'YÜKSEK' if risk_yuzde > 7 or adx < 18 else ('DÜŞÜK' if risk_yuzde < 3.5 and adx >= 25 else 'ORTA')
        vol_rejimi = volatilite_rejimi(fiyat, atr, hv20)
        risk_odul = (tp2-fiyat) / max(fiyat-stop, 1e-9)

        onceki_bb_ust = float(bb_ust.shift(1).iloc[i]) if pd.notna(bb_ust.shift(1).iloc[i]) else np.nan
        kirilim_aday = [x for x in [swing_high, onceki_bb_ust] if pd.notna(x)]
        kirilim_ref = min(kirilim_aday, default=fiyat+atr)
        breakout = fiyat >= kirilim_ref and hacim_oran >= 120 and ema9.iloc[i] > ema21.iloc[i] and uzun_vade_trend

        on_sinyal = 'Nötr (İzle) ⚖️'
        if breakout:
            on_sinyal = 'YÜKSELİŞ KIRILIMI 🚀'
        elif fiyat > float(bb_ust.iloc[i]) and rsi >= 68:
            on_sinyal = 'MOMENTUM AŞIRI ISINDI 🟡'
        elif fiyat <= float(bb_alt.iloc[i]) and rsi <= 35 and uzun_vade_trend and (mfi <= 40 or gunluk_degisim > 0):
            on_sinyal = 'KUSURSUZ ALIM 🟢'
        elif rsi <= 40 and uzun_vade_trend and fiyat <= float(bb_mid.iloc[i]) and fiyat <= (karma_destek + atr):
            on_sinyal = 'KADEMELİ ALIM 🔵'
        elif uzun_vade_trend and skor >= 70:
            on_sinyal = 'UZUN VADELİ ADAY 🌟'
        elif hacim_patlamasi and rsi < 50:
            on_sinyal = 'HACİMLİ TEPKİ 🟡'
        elif not uzun_vade_trend:
            on_sinyal = 'KURTULUŞ ÇABASI 🧗' if fiyat > float(ema50.iloc[i]) else 'UZAK DUR! 🛑'

        giris_proxy = _backtest_giris_proxy(
            on_sinyal, skor, hacim_oran, bool(ema9.iloc[i] > ema21.iloc[i]),
            bool(macd.iloc[i] > macd_signal.iloc[i]), adx, cmf, supertrend, rsi, mfi,
        )
        profil = nihai_karar_motoru(
            on_sinyal, skor, giris_proxy, fiyat,
            float(ema9.iloc[i]), float(ema21.iloc[i]), float(ema50.iloc[i]), float(sma200.iloc[i]),
            rsi, float(macd.iloc[i]), float(macd_signal.iloc[i]), cmf, mfi,
            float(bb_ust.iloc[i]), adx,
        )
        panel_ek = {
            'fiyat': fiyat, 'adx': adx, 'plus_di': plus_di, 'minus_di': minus_di,
            'cmf': cmf, 'supertrend': supertrend, 'vwap': np.nan, 'mtf_uyum': mtf_uyum,
            'sektorel_fark': np.nan, 'risk_odul': risk_odul, 'risk_seviyesi': risk_seviyesi,
        }
        guven = sinyal_guven_skoru(panel_ek, skor)
        karar = merkezi_karar_motoru({
            **panel_ek,
            'profil': profil, 'on_sinyal': on_sinyal, 'nihai_skor': skor,
            'giris_puani': giris_proxy, 'giris_asamasi': 'DAILY_PROXY',
            'tetik_sahte_kirilim': False, 'guven_skoru': guven,
            'volatilite_rejimi': vol_rejimi,
            'ema9': float(ema9.iloc[i]), 'ema21': float(ema21.iloc[i]),
            'ema50': float(ema50.iloc[i]), 'sma200': float(sma200.iloc[i]),
            'rsi': rsi, 'mfi': mfi, 'macd': float(macd.iloc[i]),
            'macd_signal': float(macd_signal.iloc[i]), 'bb_ust': float(bb_ust.iloc[i]),
        })

        # Backtest işlemi yalnızca merkezi motorun alım yönlü gerçek aksiyon sınıflarında açılır.
        if karar.get('aksiyon') not in {'GUCLU_AL', 'AL', 'ERKEN_AL'}:
            continue

        row = {
            'Tarih': df.index[i],
            'Sinyal': karar.get('karar', 'AL'),
            'Teknik Profil': profil,
            'Ön Sinyal': on_sinyal,
            'Hibrit Skor': skor,
            'Güven %': guven,
            'Daily MTF %': mtf_uyum,
            'Giriş Proxy': giris_proxy,
            'Giriş': fiyat,
            'İlk Stop': float(stop),
            'İlk TP1': tp1, 'İlk TP2': tp2, 'İlk TP3': tp3,
        }
        for ufuk in [5, 10, 20, 45]:
            row[f'{ufuk}G %'] = float((c.iloc[i+ufuk] / fiyat - 1) * 100) if i+ufuk < len(df) else np.nan

        son_i = min(i+45, len(df)-1)
        ilk_olay = '45G SÜRE SONU'
        cikis_i = son_i
        cikis_fiyati = float(c.iloc[son_i])
        tp1_gordu = tp2_gordu = tp3_gordu = stop_gordu = False
        belirsiz = False
        for j in range(i+1, son_i+1):
            gun_low, gun_high = float(l.iloc[j]), float(h.iloc[j])
            stop_hit = gun_low <= stop
            tp1_hit = gun_high >= tp1
            tp2_gordu = tp2_gordu or gun_high >= tp2
            tp3_gordu = tp3_gordu or gun_high >= tp3
            stop_gordu = stop_gordu or stop_hit
            tp1_gordu = tp1_gordu or tp1_hit
            if stop_hit and tp1_hit:
                belirsiz = True; ilk_olay = 'STOP (AYNI GÜN TP1 DE GÖRÜLDÜ)'; cikis_i = j; cikis_fiyati = stop; break
            if stop_hit:
                ilk_olay = 'STOP'; cikis_i = j; cikis_fiyati = stop; break
            if tp1_hit:
                ilk_olay = 'TP1'; cikis_i = j; cikis_fiyati = tp1; break

        row.update({
            'İlk Olay': ilk_olay, 'Çıkış Tarihi': df.index[cikis_i],
            'İşlem Sonucu %': float((cikis_fiyati/fiyat - 1)*100),
            'Pozisyonda İşlem Günü': int(cikis_i-i),
            'TP1 Gördü': bool(tp1_gordu), 'TP2 Gördü': bool(tp2_gordu), 'TP3 Gördü': bool(tp3_gordu),
            'Stop Gördü': bool(stop_gordu), 'Aynı Gün Belirsiz': bool(belirsiz),
        })
        rows.append(row)
        sonraki_yeni_giris = cikis_i + 1

    out = pd.DataFrame(rows)
    if out.empty:
        return out, {}
    for col in ['20G %', '45G %', 'İşlem Sonucu %']:
        out[col] = pd.to_numeric(out[col], errors='coerce')
    trade = out['İşlem Sonucu %'].dropna()
    stats = {
        'sinyal': len(out),
        'kazanma20': float((out['20G %'].dropna() > 0).mean()*100) if out['20G %'].notna().any() else 0.0,
        'ort20': float(out['20G %'].mean()), 'medyan20': float(out['20G %'].median()),
        'kazanma45': float((out['45G %'].dropna() > 0).mean()*100) if out['45G %'].notna().any() else 0.0,
        'ort45': float(out['45G %'].mean()),
        'islem_basarisi': float((trade > 0).mean()*100) if len(trade) else 0.0,
        'islem_ort': float(trade.mean()) if len(trade) else 0.0,
        'tp1_oran': float((out['İlk Olay'] == 'TP1').mean()*100),
        'stop_oran': float(out['İlk Olay'].astype(str).str.startswith('STOP').mean()*100),
        'belirsiz': int(out['Aynı Gün Belirsiz'].sum()),
    }
    return out, stats


def ogrenme_profili_olustur(kayitlar):
    if not kayitlar: return pd.DataFrame()
    df=pd.DataFrame(kayitlar)
    if df.empty or 'sinyal' not in df or 'getiri_yuzde' not in df: return pd.DataFrame()
    df['getiri_yuzde']=pd.to_numeric(df['getiri_yuzde'],errors='coerce')
    df['rsi']=pd.to_numeric(df.get('rsi'),errors='coerce')
    df['RSI Dilimi']=pd.cut(df['rsi'],[0,30,35,40,50,60,70,100],include_lowest=True)
    g=df.groupby(['sinyal','RSI Dilimi'],observed=True)['getiri_yuzde'].agg(['count','mean',lambda x:(x>0).mean()*100]).reset_index()
    g.columns=['Sinyal','RSI Dilimi','Örnek','Ort. Getiri %','Başarı %']
    return g[g['Örnek']>=3].sort_values(['Başarı %','Örnek'],ascending=False)

# --- AKILLI AKSİYON REHBERİ ---
def aksiyon_rehberi_olustur(nihai_sinyal, teyit_5dk, profil=None, karar_detay=None):
    """Nihai aksiyonu ve teknik profili tek merkezi kararın diliyle açıklar."""
    sinyal_metni = str(nihai_sinyal).upper()
    profil_metni = str(profil or 'NÖTR')
    teyit_metni = str(teyit_5dk or '—')
    detay = karar_detay if isinstance(karar_detay, dict) else {}
    ozet = str(detay.get('ozet', '') or '')
    olumlu = detay.get('olumlu', []) or []
    olumsuz = detay.get('olumsuz', []) or []

    if 'GÜÇLÜ AL' in sinyal_metni:
        renk, baslik = '#2ecc71', '🚀 GÜÇLÜ AL — ÇOKLU TEYİT TAMAMLANDI'
        ana_metin = ('Ana trend, giriş kalitesi, algoritma güveni ve çoklu zaman dilimi teyitleri aynı yönde güçlenmiştir. '
                     'Bu karar yalnızca yüksek giriş puanına değil, trend, momentum, para akışı ve risk filtrelerinin birlikte geçilmesine dayanır.')
    elif sinyal_metni.startswith('AL ') or sinyal_metni == 'AL':
        renk, baslik = '#27ae60', '🟢 AL — TEKNİK TEYİT YETERLİ'
        ana_metin = ('Teknik yapı alım yönünü destekliyor ve gerekli teyitlerin çoğu sağlanmış durumda. '
                     'Yine de pozisyon büyüklüğü, stop ve risk/ödül planı korunmalıdır.')
    elif 'ERKEN AL' in sinyal_metni:
        renk, baslik = '#16a085', '🟢 ERKEN AL — OLUMLU YAPI, TAM TEYİT HENÜZ YOK'
        ana_metin = ('Trend yapısı olumlu ve giriş motoru güçleniyor; ancak güçlü alım için aranan tüm filtreler henüz tamamlanmış değil. '
                     'Bu nedenle sinyal daha erken ve daha yüksek hata paylı bir giriş sınıfıdır.')
    elif 'TEYİT BEKLE' in sinyal_metni:
        renk, baslik = '#f1c40f', '🟡 TEYİT BEKLE — ADAYLIK OLUMLU, AKSİYON HENÜZ ONAYLI DEĞİL'
        ana_metin = ('Varlığın teknik profili veya bulunduğu fiyat bölgesi olumlu olabilir; fakat algoritma güveni, para akışı, trend gücü, '
                     'çoklu zaman dilimi veya giriş teyitlerinden en az biri final AL kararını destekleyecek seviyeye ulaşmamıştır.')
    elif any(x in sinyal_metni for x in ['KÂR AL', 'KAR AL', 'KÂR KORU', 'KAR KORU']):
        renk, baslik = '#e67e22', '🟠 KÂR KORU / RİSK AZALT — YENİ GİRİŞ İÇİN UYGUN DEĞİL'
        ana_metin = ('Trend tamamen bozulmuş olmak zorunda değildir; ancak aşırı ısınma veya momentum bozulması nedeniyle yeni girişin risk/getirisi zayıflamıştır. '
                     'Mevcut pozisyonda kâr koruma, stop yükseltme veya kademeli risk azaltma yaklaşımı öne çıkar.')
    elif 'SAT / KAÇIN' in sinyal_metni or 'RİSKTEN KAÇIN' in sinyal_metni:
        renk, baslik = '#e74c3c', '🔴 SAT / KAÇIN — SERMAYE KORUMA ÖNCELİKLİ'
        ana_metin = ('Ana trend ve/veya risk filtreleri yeni pozisyon için yeterli teknik avantaj göstermiyor. '
                     'Bu bölgede güçlü bir dönüş teyidi oluşmadan agresif girişten kaçınmak önceliklidir.')
    else:
        renk, baslik = '#95a5a6', '⚪ İZLE / NÖTR — NET AKSİYON AVANTAJI YOK'
        ana_metin = ('Göstergeler ortak ve yeterince güçlü bir işlem yönü üretmiyor. Sistem işlem üretmek yerine yeni teyit beklemeyi tercih ediyor.')

    gerekce = ozet or ('Olumlu: ' + ', '.join(olumlu[:3]) if olumlu else '')
    if not gerekce and olumsuz:
        gerekce = 'Riskler: ' + ', '.join(olumsuz[:3])
    gerekce_html = f'<div style="margin-top:12px"><b>Merkezi karar gerekçesi:</b> {gerekce}</div>' if gerekce else ''

    return f'''
    <div style="margin-top:18px;padding:18px;border-radius:10px;border-left:6px solid {renk};background:rgba(128,128,128,.08);color:inherit;line-height:1.65;">
      <h3 style="margin-top:0;color:{renk};">{baslik}</h3>
      <div><b>Teknik profil:</b> {profil_metni}</div>
      <p>{ana_metin}</p>
      {gerekce_html}
      <div style="margin-top:12px;padding:10px;background:rgba(128,128,128,.08);border-radius:6px;"><b>Giriş motoru:</b> {teyit_metni}</div>
      <div style="margin-top:10px;font-size:12px;opacity:.72;">Profil, skor ve teyitler açıklayıcı katmanlardır; işlem aksiyonu yalnızca merkezi nihai karar motorundan gelir.</div>
    </div>
    '''


def _seviye_yildizi(seviye, adaylar, atr):
    """Yakın teknik referansların çakışmasını 1-5 yıldızla özetler."""
    tolerans = max(float(atr) * 0.35, abs(float(seviye)) * 0.003)
    uyum = sum(1 for x in adaylar if pd.notna(x) and abs(float(x) - float(seviye)) <= tolerans)
    return min(5, max(1, uyum + 1))


def teknik_seviyeler_hesapla(df, fiyat, atr, ema50, bb_alt, bb_mid, bb_ust, hv20):
    """Geçmiş tepe/dipler, bantlar, ATR ve volatilite projeksiyonundan S/R ve TP üretir."""
    fiyat, atr = float(fiyat), max(float(atr), fiyat * 0.005)
    gecmis = df.iloc[:-1].copy() if len(df) > 2 else df.copy()
    highs = [gecmis['High'].tail(n).max() for n in (20, 50, 100) if len(gecmis) >= min(n, 10)]
    lows = [gecmis['Low'].tail(n).min() for n in (20, 50, 100) if len(gecmis) >= min(n, 10)]
    swing_range = max((max(highs) - min(lows)) if highs and lows else atr * 4, atr * 2)
    hv_45 = fiyat * max(float(hv20), 0.05) * np.sqrt(45 / 252)

    direncler = highs + [bb_ust, fiyat + atr * 1.5, fiyat + atr * 3.0,
                         fiyat + swing_range * 0.272, fiyat + swing_range * 0.618,
                         fiyat + hv_45]
    destekler = lows + [ema50, bb_mid, bb_alt, fiyat - atr, fiyat - atr * 2,
                        fiyat - hv_45]

    def sec(adaylar, ust=True):
        vals = sorted({round(float(x), 6) for x in adaylar if pd.notna(x) and ((x > fiyat) if ust else (x < fiyat))}, reverse=not ust)
        secilen=[]
        for x in vals:
            if not secilen or all(abs(x-y) >= atr*0.35 for y in secilen):
                secilen.append(x)
            if len(secilen)==3: break
        while len(secilen)<3:
            adim=(len(secilen)+1)*atr*(1.5 if ust else -1.0)
            x=fiyat+adim
            if all(abs(x-y)>=atr*0.25 for y in secilen): secilen.append(x)
        return sorted(secilen) if ust else sorted(secilen, reverse=True)

    r=sec(direncler, True); d=sec(destekler, False)
    return {
        's1': d[0], 's2': d[1], 's3': d[2],
        'r1': r[0], 'r2': r[1], 'r3': r[2],
        'tp1': r[0], 'tp2': r[1], 'tp3': r[2],
        'tp1_yildiz': _seviye_yildizi(r[0], direncler, atr),
        'tp2_yildiz': _seviye_yildizi(r[1], direncler, atr),
        'tp3_yildiz': _seviye_yildizi(r[2], direncler, atr),
    }


def nihai_karar_motoru(on_sinyal, skor, tetik_puani, fiyat, ema9, ema21, ema50,
                       sma200, rsi, macd, macd_sinyal, cmf, mfi, bb_ust, adx):
    """Trend, momentum, risk ve giriş kalitesi çelişkilerini tek bir nihai kararda çözer."""
    trend_guclu = fiyat > sma200 and fiyat > ema50 and ema9 > ema21
    momentum_pozitif = macd > macd_sinyal and cmf >= 0
    asiri_isinmis = rsi >= 68 and fiyat >= bb_ust * 0.995
    momentum_bozuluyor = macd <= macd_sinyal or fiyat < ema9 or cmf < 0 or mfi < 45

    if asiri_isinmis and trend_guclu and momentum_pozitif and tetik_puani >= 60:
        return 'MOMENTUM AŞIRI ISINDI 🟡'
    if rsi >= 70 and momentum_bozuluyor and tetik_puani < 60:
        return 'KAR REALİZASYONU 🔴'
    if tetik_puani >= 80 and trend_guclu and momentum_pozitif:
        return 'GÜÇLÜ KIRILIM 🚀'
    if tetik_puani >= 60 and 'KIRILIM' in str(on_sinyal):
        return 'YÜKSELİŞ KIRILIMI 🚀'
    if 'KUSURSUZ ALIM' in str(on_sinyal) and not momentum_bozuluyor:
        return on_sinyal
    if 'KADEMELİ ALIM' in str(on_sinyal):
        return on_sinyal
    if trend_guclu and skor >= 70 and not asiri_isinmis:
        return 'UZUN VADELİ ADAY 🌟'
    if not trend_guclu and skor < 45:
        return 'UZAK DUR! 🛑'
    return on_sinyal

def sozlu_teknik_analiz_olustur(ticker, fiyat, gunluk_degisim, rsi, macd, macd_sinyal,
                                  ema9, ema21, ema50, sma200, bb_alt, bb_mid, bb_ust,
                                  hacim_oran, mfi, sektorel_fark, destek, direnc, stop,
                                  tp1, tp2, tp3, sinyal, veri_kaynagi):
    trend_uzun = "yukarı" if fiyat > sma200 else "aşağı"
    trend_orta = "pozitif" if fiyat > ema50 else "zayıf"
    trend_kisa = "boğa lehine" if ema9 > ema21 else "ayı lehine"

    if rsi >= 70:
        rsi_yorum = "RSI aşırı alım bölgesinde; yeni alımda acele etmek yerine kâr koruma ve geri çekilme riski izlenmeli."
    elif rsi <= 30:
        rsi_yorum = "RSI aşırı satım bölgesinde; tepki ihtimali artsa da dönüş teyidi olmadan risk yüksektir."
    elif rsi <= 40:
        rsi_yorum = "RSI zayıf bölgede; fiyatın destek çevresindeki davranışı ve kısa vadeli teyit önem taşıyor."
    elif rsi <= 60:
        rsi_yorum = "RSI dengeli bölgede; fiyatın yön seçmesi için uygun, aşırılaşmamış bir yapı var."
    else:
        rsi_yorum = "RSI güçlü bölgede; momentum olumlu olmakla birlikte aşırı alıma yaklaşma riski izlenmeli."

    macd_yorum = "MACD, sinyal çizgisinin üzerinde ve momentum yükselişi destekliyor." if macd > macd_sinyal else "MACD, sinyal çizgisinin altında; kısa vadeli momentum henüz tam destek vermiyor."
    hacim_yorum = (
        "Hacim 20 günlük ortalamanın belirgin üzerinde; hareketin katılımı güçlü." if hacim_oran >= 130 else
        "Hacim ortalamanın üzerinde; fiyat hareketi destek buluyor." if hacim_oran >= 100 else
        "Hacim ortalamanın altında; mevcut hareketin teyidi sınırlı."
    )
    mfi_yorum = (
        "MFI para girişinin yoğunlaştığını gösteriyor." if mfi >= 70 else
        "MFI para çıkışının baskın olduğuna işaret ediyor." if mfi <= 30 else
        "MFI dengeli para akışına işaret ediyor."
    )
    if pd.isna(sektorel_fark) or not np.isfinite(float(sektorel_fark)):
        sektor_yorum = "Göreceli güç için yeterli ve temiz referans verisi bulunamadı; bu alan skorlamada nötr bırakıldı."
    elif sektorel_fark >= 0:
        sektor_yorum = f"Varlık son bir ayda referansına göre %{sektorel_fark:.1f} daha güçlü performans gösteriyor."
    else:
        sektor_yorum = f"Varlık son bir ayda referansının %{abs(sektorel_fark):.1f} gerisinde kalıyor."
    bant_yorum = (
        "Fiyat üst Bollinger bandına yakın; kısa vadede şişkinlik ve kâr satışı riski artmış durumda." if fiyat >= bb_ust * 0.995 else
        "Fiyat alt Bollinger bandına yakın; tepki olasılığı artsa da zayıflık devam ediyor." if fiyat <= bb_alt * 1.005 else
        "Fiyat Bollinger bantlarının içinde; hareket henüz aşırılaşmış görünmüyor."
    )

    return f"""
    <div style="background:rgba(128,128,128,.08);border:1px solid rgba(128,128,128,.25);border-radius:12px;padding:20px;margin-top:18px;color:inherit;line-height:1.65;">
      <h3 style="margin:0 0 12px 0;color:#ffffff;">🧠 {ticker} Sözel Teknik Analizi</h3>
      <p><b>Genel görünüm:</b> Fiyat {fiyat:.2f} seviyesinde ve günlük değişim %{gunluk_degisim:+.2f}. Uzun vadeli ana trend <b>{trend_uzun}</b>, orta vadeli yapı <b>{trend_orta}</b>, EMA 9/21 ilişkisi ise <b>{trend_kisa}</b>.</p>
      <p><b>Momentum:</b> {rsi_yorum} {macd_yorum}</p>
      <p><b>Hacim ve para akışı:</b> {hacim_yorum} {mfi_yorum}</p>
      <p><b>Göreceli güç:</b> {sektor_yorum}</p>
      <p><b>Volatilite ve konum:</b> {bant_yorum}</p>
      <p><b>Kritik seviyeler:</b> Yakın destek <b>{destek:.2f}</b>, direnç <b>{direnc:.2f}</b>, süren stop <b>{stop:.2f}</b>. Olumlu senaryoda izlenebilecek hedefler <b>{tp1:.2f}</b>, <b>{tp2:.2f}</b> ve trend devamında <b>{tp3:.2f}</b>.</p>
      <p><b>Sistem sonucu:</b> {sinyal}. Veri kaynağı: <b>{veri_kaynagi}</b>.</p>
      <div style="margin-top:12px;padding:10px 12px;border-left:4px solid #3498db;background:rgba(52,152,219,.10);border-radius:6px;">
        Bu bölüm otomatik teknik göstergelere dayanır; tek başına yatırım kararı yerine trend, hacim, destek/direnç ve risk yönetimi birlikte değerlendirilmelidir.
      </div>
    </div>
    """

def gelismis_teknik_panel_olustur(d):
    """Grafik yerine sade, tema uyumlu ve açıklanabilir teknik gösterge paneli üretir."""
    fiyat = float(d["fiyat"])
    ema9, ema21, ema50, sma200 = map(float, (d["ema9"], d["ema21"], d["ema50"], d["sma200"]))
    rsi, mfi = float(d["rsi"]), float(d["mfi"])
    macd, macd_signal = float(d["macd"]), float(d["macd_signal"])
    macd_hist = macd - macd_signal
    atr, obv, obv_ema = float(d["atr"]), float(d["obv"]), float(d["obv_ema"])
    bb_alt, bb_mid, bb_ust = map(float, (d["bb_alt"], d["bb_mid"], d["bb_ust"]))
    destek, direnc, stop = map(float, (d["destek"], d["direnc"], d["stop"]))
    tp1, tp2, tp3 = float(d["tp1"]), float(d["tp2"]), float(d.get("tp3", d["tp2"]))
    s1, s2, s3 = float(d.get("s1", destek)), float(d.get("s2", d.get("swing_low", destek))), float(d.get("s3", max(0.01, destek-atr)))
    r1, r2, r3 = float(d.get("r1", direnc)), float(d.get("r2", tp2)), float(d.get("r3", tp3))
    tp1_y, tp2_y, tp3_y = int(d.get("tp1_yildiz",3)), int(d.get("tp2_yildiz",2)), int(d.get("tp3_yildiz",1))
    hacim, hacim_ort, hacim_oran = float(d["hacim"]), float(d["hacim_ort"]), float(d["hacim_oran"])
    sinyal, veri_kaynagi = str(d["sinyal"]), str(d["veri_kaynagi"])
    profil = str(d.get("profil", d.get("on_sinyal", "NÖTR")))
    seans_disi = str(d.get("seans_disi", "—"))
    seans_notu = f" · {seans_disi} (ek bilgi; skora dahil değil)" if seans_disi and seans_disi != "—" else ""
    gunluk_degisim, ticker = float(d["gunluk_degisim"]), str(d["ticker"])
    tetik_puani = int(d.get("giris_puani", d.get("tetik_puani", 0)) or 0)
    tetik_seviyesi = str(d.get("giris_seviyesi", d.get("tetik_seviyesi", "⏳ GİRİŞ UYGUN DEĞİL")))
    tetik_detay = d.get("giris_detay", d.get("tetik_detay", [])) or []
    skor = int(d.get("nihai_skor", d.get("cezali_skor", d.get("skor", 0))) or 0)
    guven = int(d.get("guven_skoru", 0) or 0)

    def durum(deger, olumlu, olumsuz):
        return ("pozitif", olumlu) if deger else ("negatif", olumsuz)

    trend_uzun_cls, trend_uzun = durum(fiyat > sma200, "Ana trend yukarı", "Ana trend aşağı")
    trend_orta_cls, trend_orta = durum(fiyat > ema50, "Orta trend yukarı", "Orta trend aşağı")
    trend_kisa_cls, trend_kisa = durum(ema9 > ema21, "Kısa trend yukarı", "Kısa trend aşağı")
    macd_cls, macd_txt = durum(macd > macd_signal, "Momentum güçleniyor", "Momentum zayıflıyor")
    obv_cls, obv_txt = durum(obv > obv_ema, "OBV yükseliyor", "OBV düşüyor")

    if rsi >= 70:
        rsi_cls, rsi_txt = "uyari", "Aşırı alım"
    elif rsi <= 30:
        rsi_cls, rsi_txt = "uyari", "Aşırı satım"
    elif 45 <= rsi <= 65:
        rsi_cls, rsi_txt = "pozitif", "Dengeli momentum"
    else:
        rsi_cls, rsi_txt = "notr", "Zayıf / nötr"

    if tetik_puani >= 80:
        tetik_cls = "pozitif"
    elif tetik_puani >= 40:
        tetik_cls = "uyari"
    else:
        tetik_cls = "notr"

    def metric(icon, title, value, note, css="notr"):
        return f'<div class="hp-card"><div class="hp-card-head"><span>{icon}</span><span>{title}</span></div><div class="hp-card-value">{value}</div><div class="hp-pill {css}">{note}</div></div>'

    cards = "".join([
        metric("💵", "Fiyat", f"{fiyat:.2f}", f"%{gunluk_degisim:+.2f}", "pozitif" if gunluk_degisim >= 0 else "negatif"),
        metric("📈", "EMA 9 / 21", f"{ema9:.2f} / {ema21:.2f}", trend_kisa, trend_kisa_cls),
        metric("🧭", "EMA 50 / SMA 200", f"{ema50:.2f} / {sma200:.2f}", trend_uzun, trend_uzun_cls),
        metric("⚡", "RSI (14)", f"{rsi:.2f}", rsi_txt, rsi_cls),
        metric("📊", "MACD Histogram", f"{macd_hist:.3f}", macd_txt, macd_cls),
        metric("🎯", "Giriş Kalitesi", f"{tetik_puani}/100", tetik_seviyesi, tetik_cls),
        metric("💧", "MFI / OBV", f"{mfi:.1f} / {obv:,.0f}", obv_txt, obv_cls),
        metric("🌊", "ATR (14)", f"{atr:.2f}", "Yüksek oynaklık" if atr/max(fiyat,1e-9) > .035 else "Normal oynaklık", "uyari" if atr/max(fiyat,1e-9) > .035 else "notr"),
    ])

    tetik_list = "".join(f"<li>{x}</li>" for x in tetik_detay[:7]) or "<li>Henüz yeterli çok zaman dilimli giriş teyidi bulunmuyor.</li>"
    karar_cls = ("pozitif" if sinyal_yonu_belirle(sinyal) == "ALIM" else
                 "negatif" if sinyal_yonu_belirle(sinyal) == "SATIŞ" else
                 "uyari" if any(x in sinyal for x in ["TEYİT", "KÂR", "KAR", "🟠", "🟡"]) else "notr")
    yildiz = lambda n: "★"*max(1,min(5,n)) + "☆"*(5-max(1,min(5,n)))
    bollinger_konum = "Üst banda yakın" if fiyat >= bb_ust*.985 else "Alt banda yakın" if fiyat <= bb_alt*1.015 else "Bant içinde"
    ana_yorum = "SMA 200 üzerinde ana yükseliş yapısını koruyor" if fiyat > sma200 else "SMA 200 altında ve ana trend baskı altında"
    kisa_yorum = "EMA 21 üzerinde" if ema9 > ema21 else "EMA 21 altında"

    return f"""
    <style>
      .hp-wrap{{margin-top:14px;padding:18px;border:1px solid rgba(128,128,128,.28);border-radius:14px;background:var(--secondary-background-color);color:var(--text-color);font-family:inherit}}
      .hp-head{{display:flex;justify-content:space-between;align-items:flex-start;gap:12px;flex-wrap:wrap;margin-bottom:14px}}
      .hp-title{{font-size:22px;font-weight:750;line-height:1.25}} .hp-sub{{font-size:12px;opacity:.68;margin-top:4px}}
      .hp-source{{font-size:12px;padding:5px 9px;border:1px solid rgba(49,130,206,.35);border-radius:999px;background:rgba(49,130,206,.08)}}
      .hp-grid{{display:grid;grid-template-columns:repeat(4,minmax(150px,1fr));gap:10px}}
      .hp-card{{padding:13px;border:1px solid rgba(128,128,128,.22);border-radius:10px;background:var(--background-color);min-height:104px}}
      .hp-card-head{{display:flex;gap:7px;align-items:center;font-size:12px;font-weight:650;opacity:.78}}
      .hp-card-value{{font-size:23px;font-weight:750;margin:8px 0 7px;letter-spacing:-.3px}}
      .hp-pill{{display:inline-block;font-size:11px;padding:4px 8px;border-radius:999px;background:rgba(128,128,128,.12)}}
      .hp-pill.pozitif,.hp-positive{{color:#1f9d55;background:rgba(31,157,85,.11)}}
      .hp-pill.negatif,.hp-negative{{color:#d64545;background:rgba(214,69,69,.10)}}
      .hp-pill.uyari,.hp-warning{{color:#b7791f;background:rgba(183,121,31,.12)}}
      .hp-pill.notr{{opacity:.75}}
      .hp-sections{{display:grid;grid-template-columns:1.05fr 1fr 1fr;gap:10px;margin-top:10px}}
      .hp-section{{padding:14px;border:1px solid rgba(128,128,128,.22);border-radius:10px;background:var(--background-color)}}
      .hp-section h4{{font-size:13px;margin:0 0 10px;opacity:.82}}
      .hp-row{{display:flex;justify-content:space-between;gap:12px;padding:6px 0;border-bottom:1px solid rgba(128,128,128,.13);font-size:13px}}
      .hp-row:last-child{{border-bottom:none}} .hp-row b{{white-space:nowrap}}
      .hp-target{{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-top:8px}}
      .hp-target-card{{padding:10px;border-radius:8px;background:rgba(128,128,128,.07);text-align:center}}
      .hp-target-card strong{{display:block;font-size:18px;margin:4px 0}} .hp-stars{{font-size:12px;color:#b7791f;letter-spacing:1px}}
      .hp-comment{{margin-top:10px;padding:14px;border-left:4px solid #3182ce;border-radius:8px;background:rgba(49,130,206,.07);font-size:13px;line-height:1.65}}
      .hp-decision{{margin-top:10px;padding:14px;border:1px solid rgba(128,128,128,.22);border-radius:10px;background:var(--background-color)}}
      .hp-decision-title{{font-size:18px;font-weight:750;margin-bottom:5px}} .hp-small{{font-size:12px;opacity:.7}}
      .hp-trigger-list{{margin:8px 0 0 18px;padding:0;font-size:12px;line-height:1.6}}
      @media(max-width:1000px){{.hp-grid{{grid-template-columns:repeat(2,1fr)}}.hp-sections{{grid-template-columns:1fr}}}}
      @media(max-width:600px){{.hp-grid{{grid-template-columns:1fr}}.hp-target{{grid-template-columns:1fr}}}}
    </style>
    <div class="hp-wrap">
      <div class="hp-head"><div><div class="hp-title">📋 {ticker} — Detaylı Teknik Analiz</div><div class="hp-sub">Göstergeler, seviyeler ve nihai karar tek görünümde{seans_notu}</div></div><div class="hp-source">🔌 {veri_kaynagi}</div></div>
      <div class="hp-grid">{cards}</div>
      <div class="hp-sections">
        <div class="hp-section"><h4>🧭 Trend ve momentum özeti</h4>
          <div class="hp-row"><span>Ana trend</span><b class="hp-{trend_uzun_cls}">{trend_uzun}</b></div>
          <div class="hp-row"><span>Orta trend</span><b class="hp-{trend_orta_cls}">{trend_orta}</b></div>
          <div class="hp-row"><span>Kısa trend</span><b class="hp-{trend_kisa_cls}">{trend_kisa}</b></div>
          <div class="hp-row"><span>Bollinger konumu</span><b>{bollinger_konum}</b></div>
          <div class="hp-row"><span>Hacim / ortalama</span><b>%{hacim_oran:.0f}</b></div>
        </div>
        <div class="hp-section"><h4>🛡️ Destek ve direnç bölgeleri</h4>
          <div class="hp-row"><span>S1 — Yakın destek</span><b>{s1:.2f}</b></div><div class="hp-row"><span>S2 — Ana destek</span><b>{s2:.2f}</b></div><div class="hp-row"><span>S3 — Derin risk</span><b>{s3:.2f}</b></div>
          <div class="hp-row"><span>R1 — İlk direnç</span><b>{r1:.2f}</b></div><div class="hp-row"><span>R2 — İkinci direnç</span><b>{r2:.2f}</b></div><div class="hp-row"><span>R3 — Trend direnci</span><b>{r3:.2f}</b></div>
          <div class="hp-row"><span>Teknik stop</span><b class="hp-negative">{stop:.2f}</b></div>
        </div>
        <div class="hp-section"><h4>🎯 Çok zaman dilimli giriş motoru</h4><div class="hp-row"><span>Puan</span><b>{tetik_puani}/100</b></div><div class="hp-row"><span>Seviye</span><b>{tetik_seviyesi}</b></div><ul class="hp-trigger-list">{tetik_list}</ul></div>
      </div>
      <div class="hp-section" style="margin-top:10px"><h4>🎯 Teknik kâr hedefleri</h4><div class="hp-target">
        <div class="hp-target-card"><span>TP1 — Yakın hedef</span><strong>{tp1:.2f}</strong><div class="hp-stars">{yildiz(tp1_y)}</div></div>
        <div class="hp-target-card"><span>TP2 — Orta hedef</span><strong>{tp2:.2f}</strong><div class="hp-stars">{yildiz(tp2_y)}</div></div>
        <div class="hp-target-card"><span>TP3 — Agresif trend</span><strong>{tp3:.2f}</strong><div class="hp-stars">{yildiz(tp3_y)}</div></div>
      </div></div>
      <div class="hp-comment"><b>🧠 Algoritmik yorum:</b> Fiyat {ana_yorum}. Kısa vadede EMA 9 {kisa_yorum}, RSI {rsi:.1f} ve MACD histogramı {macd_hist:.3f}. Hacim 20 günlük ortalamanın %{hacim_oran:.0f} seviyesinde; fiyatın {s1:.2f}–{r1:.2f} karar aralığındaki davranışı yönün devamı açısından önemlidir.</div>
      <div class="hp-decision"><div class="hp-decision-title">🧭 Nihai karar: <span class="hp-pill {karar_cls}">{sinyal}</span></div><div style="margin-top:5px"><b>Teknik profil:</b> {profil}</div><div>Hibrit skor: <b>{skor}/100</b> · Algoritma güveni: <b>%{guven}</b> · Giriş kalitesi: <b>{tetik_puani}/100</b></div><div class="hp-small" style="margin-top:6px">Profil ve skorlar açıklayıcıdır; işlem aksiyonu merkezi karar motorundan gelir.</div></div>
    </div>
    """

def sinyal_yonu_belirle(sinyal):
    """Nihai aksiyonu işlem yönüne çevirir; eski kayıt etiketleriyle de uyumludur."""
    metin = str(sinyal).upper()
    if any(x in metin for x in ['SAT / KAÇIN', 'RİSKTEN KAÇIN', 'UZAK DUR', 'KAR REALİZASYONU', 'KÂR REALİZASYONU', 'KAR AL', 'KÂR AL']):
        return 'SATIŞ'
    if any(x in metin for x in ['TEYİT BEKLE', 'İZLE', 'NÖTR', 'KÂR KORU', 'KAR KORU']):
        return 'NÖTR'
    if any(x in metin for x in ['GÜÇLÜ AL', 'ERKEN AL', 'AL 🟢', 'KUSURSUZ ALIM', 'KADEMELİ ALIM', 'YÜKSELİŞ KIRILIMI', 'GÜÇLÜ KIRILIM']):
        return 'ALIM'
    return 'NÖTR'


@st.cache_data(ttl=1800, show_spinner=False)
def _donem_ohlc_cek(ticker, baslangic_iso, bitis_iso):
    try:
        bas = pd.to_datetime(baslangic_iso, errors="coerce")
        bit = pd.to_datetime(bitis_iso, errors="coerce")
        if pd.isna(bas) or pd.isna(bit):
            return pd.DataFrame()
        df = yf.download(ticker, start=(bas-pd.Timedelta(days=2)).date().isoformat(), end=(bit+pd.Timedelta(days=2)).date().isoformat(), interval="1d", progress=False, auto_adjust=True, threads=False, timeout=8)
        return _normalize_yf_columns(df)
    except Exception as e:
        izfin_hata_logla("kapanan_donem_ohlc", e, ticker)
        return pd.DataFrame()


def kapanan_donem_istatistikleri(ticker, giris, acilis_zamani, kapanis_zamani, ilk_stop=None, ilk_tp1=None, ilk_tp2=None, ilk_tp3=None):
    sonuc={"donem_max_kar":None,"donem_max_dusus":None,"ilk_tp1_gordu":None,"ilk_tp2_gordu":None,"ilk_tp3_gordu":None,"ilk_stop_gordu":None}
    try:
        giris=float(giris)
        if not np.isfinite(giris) or giris<=0: return sonuc
        bas=pd.to_datetime(acilis_zamani,errors="coerce"); bit=pd.to_datetime(kapanis_zamani,errors="coerce")
        if pd.isna(bas) or pd.isna(bit): return sonuc
        df=_donem_ohlc_cek(ticker,str(acilis_zamani),str(kapanis_zamani))
        if df is None or df.empty or "High" not in df.columns or "Low" not in df.columns: return sonuc
        idx=pd.to_datetime(df.index)
        try:
            if getattr(idx,"tz",None) is not None: idx=idx.tz_localize(None)
        except Exception: pass
        dfx=df.copy(); dfx.index=idx
        bas_n=pd.Timestamp(bas); bit_n=pd.Timestamp(bit)
        try:
            if bas_n.tzinfo is not None: bas_n=bas_n.tz_localize(None)
            if bit_n.tzinfo is not None: bit_n=bit_n.tz_localize(None)
        except Exception: pass
        dfx=dfx[(dfx.index.normalize()>=bas_n.normalize()) & (dfx.index.normalize()<=bit_n.normalize())]
        if dfx.empty: return sonuc
        max_high=float(pd.to_numeric(dfx["High"],errors="coerce").max()); min_low=float(pd.to_numeric(dfx["Low"],errors="coerce").min())
        if np.isfinite(max_high): sonuc["donem_max_kar"]=((max_high/giris)-1)*100
        if np.isfinite(min_low): sonuc["donem_max_dusus"]=((min_low/giris)-1)*100
        def up(v):
            try:
                v=float(v); return bool(np.isfinite(v) and v>0 and np.isfinite(max_high) and max_high>=v)
            except Exception: return None
        def down(v):
            try:
                v=float(v); return bool(np.isfinite(v) and v>0 and np.isfinite(min_low) and min_low<=v)
            except Exception: return None
        sonuc["ilk_tp1_gordu"]=up(ilk_tp1); sonuc["ilk_tp2_gordu"]=up(ilk_tp2); sonuc["ilk_tp3_gordu"]=up(ilk_tp3); sonuc["ilk_stop_gordu"]=down(ilk_stop)
        return sonuc
    except Exception as e:
        izfin_hata_logla("kapanan_donem_istatistik", e, ticker); return sonuc

def sinyal_kayitlarini_firestore_yaz(sonuclar, teknik_paneller):
    """İlk alım fiyatını koruyan, tekrar kayıt üretmeyen pozisyon takibi.

    - İlk ALIM/KIRILIM/ADAY sinyalinde tek açık pozisyon oluşturur.
    - Aynı pozisyon sürerken giriş tarihi ve giriş fiyatı asla değişmez.
    - Sinyal türü değişirse yalnızca güncel sinyal/teknik alanlar güncellenir.
    - Alım yönü kaybolursa pozisyon kapanır ve geçmişe taşınır.
    - Aynı hissede daha sonra yeniden alım oluşursa yeni dönem kaydı açılır.
    - Eski sürümlerden kalan açık arşiv kaydı varsa yeni kayıt açmak yerine
      en eski açık kaydı aktif pozisyon olarak yeniden bağlar.
    """
    if not db or not st.session_state.user_email:
        return

    simdi = datetime.now()
    email = st.session_state.user_email
    email_anahtari = email.replace("@", "_").replace(".", "_")

    # Eski sürümlerden kalan, aktif_sinyaller belgesiyle bağlantısı kopmuş açık
    # kayıtları bir kez okuyup ticker -> en eski açık pozisyon haritası oluştur.
    eski_acik_haritasi = {}
    try:
        sorgu = (db.collection("sinyal_arsivi")
                 .where("user_email", "==", email)
                 .limit(500))
        for doc in sorgu.stream():
            veri = doc.to_dict() or {}
            if veri.get("yon") != "ALIM":
                continue
            durum = str(veri.get("durum", "ACIK") or "ACIK").upper()
            if durum != "ACIK":
                continue
            ticker_eski = veri.get("ticker")
            if not ticker_eski:
                continue
            tarih = str(veri.get("olusturma_zamani", ""))
            mevcut = eski_acik_haritasi.get(ticker_eski)
            if mevcut is None or tarih < mevcut[1]:
                eski_acik_haritasi[ticker_eski] = (doc.id, tarih, veri)
    except Exception:
        eski_acik_haritasi = {}

    for sonuc in sonuclar:
        ticker = sonuc.get("Varlık")
        if not ticker:
            continue

        panel = teknik_paneller.get(ticker, {})
        sinyal = sonuc.get("Nihai Sinyal", "Nötr")
        yon = sinyal_yonu_belirle(sinyal)
        aktif_doc_id = f"{email_anahtari}_{ticker.replace('.', '_')}"
        aktif_ref = db.collection("aktif_sinyaller").document(aktif_doc_id)

        try:
            aktif_snap = aktif_ref.get()
            aktif = aktif_snap.to_dict() if aktif_snap.exists else {}
        except Exception:
            continue

        aktif_mi = str(aktif.get("durum", "")).upper() == "ACIK"
        onceki_sinyal = str(aktif.get("sinyal", ""))
        arsiv_doc_id = aktif.get("arsiv_doc_id")
        fiyat = float(panel.get("fiyat", 0) or 0)

        # Aktif belge yok ama geçmişten açık arşiv kaydı varsa onu yeniden bağla.
        if not aktif_mi and ticker in eski_acik_haritasi:
            eski_id, _, eski_veri = eski_acik_haritasi[ticker]
            arsiv_doc_id = eski_id
            aktif_mi = True
            onceki_sinyal = str(eski_veri.get("sinyal", ""))
            try:
                aktif_ref.set({
                    "user_email": email,
                    "ticker": ticker,
                    "durum": "ACIK",
                    "sinyal": onceki_sinyal,
                    "arsiv_doc_id": eski_id,
                    "acilis_zamani": eski_veri.get("olusturma_zamani"),
                    "giris_fiyati": float(eski_veri.get("giris_fiyati", 0) or 0),
                    "guncelleme_zamani": simdi.isoformat(),
                }, merge=True)
                aktif = {
                    **aktif,
                    "durum": "ACIK",
                    "sinyal": onceki_sinyal,
                    "arsiv_doc_id": eski_id,
                    "giris_fiyati": float(eski_veri.get("giris_fiyati", 0) or 0),
                }
            except Exception:
                pass

        if yon == "ALIM" and panel and fiyat > 0:
            ortak_guncel = {
                "sinyal": sinyal,
                "yon": "ALIM",
                "durum": "ACIK",
                "son_fiyat": fiyat,
                "stop": float(panel.get("stop", 0) or 0),
                "tp1": float(panel.get("tp1", 0) or 0),
                "tp2": float(panel.get("tp2", 0) or 0),
                "tp3": float(panel.get("tp3", 0) or 0),
                "rsi": float(panel.get("rsi", 0) or 0),
                "tetik": panel.get("teyit", ""),
                "tetik_puani": int(panel.get("tetik_puani", 0) or 0),
                "hibrit_skor": int(panel.get("cezali_skor", panel.get("skor", 0)) or 0),
                "veri_kaynagi": panel.get("veri_kaynagi", ""),
                "guncelleme_zamani": simdi.isoformat(),
            }

            if aktif_mi and arsiv_doc_id:
                # İlk giriş bilgileri değiştirilmez. Firestore maliyetini ve gereksiz
                # belge sürümlerini azaltmak için aynı sinyal devam ederken yazma yapma.
                # Canlı fiyat, tarama panelinden; kalıcı performans fiyatı ise ilgili
                # kullanıcı düğmesinden ayrıca güncellenir.
                if onceki_sinyal == sinyal:
                    continue

                # Sinyal gerçekten değiştiğinde güncel teknik bağlamı kaydet.
                arsiv_guncelleme = dict(ortak_guncel)
                aktif_guncelleme = {
                    "user_email": email,
                    "ticker": ticker,
                    "durum": "ACIK",
                    "sinyal": sinyal,
                    "arsiv_doc_id": arsiv_doc_id,
                    "guncelleme_zamani": simdi.isoformat(),
                }
                degisim_sayisi = int(aktif.get("sinyal_degisim_sayisi", 0) or 0) + 1
                arsiv_guncelleme.update({
                    "onceki_sinyal": onceki_sinyal,
                    "son_sinyal_degisim_zamani": simdi.isoformat(),
                    "sinyal_degisim_sayisi": degisim_sayisi,
                })
                aktif_guncelleme["sinyal_degisim_sayisi"] = degisim_sayisi
                try:
                    db.collection("sinyal_arsivi").document(arsiv_doc_id).set(arsiv_guncelleme, merge=True)
                    aktif_ref.set(aktif_guncelleme, merge=True)
                except Exception:
                    pass
                continue

            # Gerçekten açık pozisyon yoksa yeni dönem başlat.
            yeni_arsiv_id = f"{aktif_doc_id}_{simdi.strftime('%Y%m%d_%H%M%S_%f')}"
            yeni_veri = {
                "user_email": email,
                "ticker": ticker,
                "sinyal": sinyal,
                "yon": "ALIM",
                "durum": "ACIK",
                "giris_fiyati": fiyat,
                "son_fiyat": fiyat,
                "stop": float(panel.get("stop", 0) or 0),
                "tp1": float(panel.get("tp1", 0) or 0),
                "tp2": float(panel.get("tp2", 0) or 0),
                "tp3": float(panel.get("tp3", 0) or 0),
                "rsi": float(panel.get("rsi", 0) or 0),
                "tetik": panel.get("teyit", ""),
                "tetik_puani": int(panel.get("tetik_puani", 0) or 0),
                "hibrit_skor": int(panel.get("cezali_skor", panel.get("skor", 0)) or 0),
                "veri_kaynagi": panel.get("veri_kaynagi", ""),
                "olusturma_zamani": simdi.isoformat(),
                "guncelleme_zamani": simdi.isoformat(),
                "getiri_yuzde": 0.0,
                "sinyal_degisim_sayisi": 0,
                # Performans karnesi için sinyal anındaki koşullar dondurulur.
                # Bu alanlar sonraki taramalarda değiştirilmez.
                "strategy_version": STRATEJI_SURUMU,
                "ilk_sinyal": sinyal,
                "ilk_stop": float(panel.get("stop", 0) or 0),
                "ilk_tp1": float(panel.get("tp1", 0) or 0),
                "ilk_tp2": float(panel.get("tp2", 0) or 0),
                "ilk_tp3": float(panel.get("tp3", 0) or 0),
                "ilk_hibrit_skor": int(panel.get("cezali_skor", panel.get("skor", 0)) or 0),
                "ilk_giris_kalitesi": int(panel.get("giris_puani", panel.get("tetik_puani", 0)) or 0),
                "ilk_algoritma_guveni": int(panel.get("guven_skoru", 0) or 0),
                "ilk_peg": float(panel.get("peg")) if panel.get("peg") is not None and np.isfinite(panel.get("peg")) else None,
                "ilk_sektorel_fark": float(panel.get("sektorel_fark")) if panel.get("sektorel_fark") is not None and np.isfinite(panel.get("sektorel_fark")) else None,
                "benchmark_ticker": "XU100.IS" if ticker.endswith(".IS") else "^IXIC",
                "performans_ufuklari": {},
            }
            try:
                db.collection("sinyal_arsivi").document(yeni_arsiv_id).set(yeni_veri)
                aktif_ref.set({
                    "user_email": email,
                    "ticker": ticker,
                    "durum": "ACIK",
                    "sinyal": sinyal,
                    "arsiv_doc_id": yeni_arsiv_id,
                    "sinyal_degisim_sayisi": 0,
                    "acilis_zamani": simdi.isoformat(),
                    "giris_fiyati": fiyat,
                    "guncelleme_zamani": simdi.isoformat(),
                })
                eski_acik_haritasi[ticker] = (yeni_arsiv_id, simdi.isoformat(), yeni_veri)
            except Exception:
                pass

        elif aktif_mi and arsiv_doc_id:
            arsiv_veri = {}
            try:
                arsiv_snap = db.collection("sinyal_arsivi").document(arsiv_doc_id).get()
                arsiv_veri = arsiv_snap.to_dict() if arsiv_snap.exists else {}
            except Exception as e:
                izfin_hata_logla("kapanis_arsiv_okuma", e, ticker)
            giris = float(aktif.get("giris_fiyati", 0) or arsiv_veri.get("giris_fiyati", 0) or 0)
            kapanis_getiri = ((fiyat - giris) / giris * 100) if fiyat > 0 and giris > 0 else 0.0
            acilis_zamani = aktif.get("acilis_zamani") or arsiv_veri.get("olusturma_zamani") or simdi.isoformat()
            donem_istat = kapanan_donem_istatistikleri(ticker, giris, acilis_zamani, simdi.isoformat(), arsiv_veri.get("ilk_stop"), arsiv_veri.get("ilk_tp1"), arsiv_veri.get("ilk_tp2"), arsiv_veri.get("ilk_tp3"))
            try:
                db.collection("sinyal_arsivi").document(arsiv_doc_id).set({"durum":"KAPALI","kapanis_sinyali":sinyal,"kapanis_fiyati":fiyat,"son_fiyat":fiyat,"getiri_yuzde":kapanis_getiri,"kapanis_zamani":simdi.isoformat(),"guncelleme_zamani":simdi.isoformat(),**donem_istat}, merge=True)
                aktif_ref.set({"durum":"KAPALI","sinyal":sinyal,"onceki_arsiv_doc_id":arsiv_doc_id,"arsiv_doc_id":None,"guncelleme_zamani":simdi.isoformat()}, merge=True)
                eski_acik_haritasi.pop(ticker, None)
            except Exception as e:
                izfin_hata_logla("pozisyon_kapatma", e, ticker)

def gecmis_mukerrer_kayitlari_temizle():
    """Mükerrerleri önce yedek koleksiyona kopyalar, sonra siler. Otomatik çalışmaz."""
    if not db or not st.session_state.user_email:
        return {"silinen":0,"yedeklenen":0,"grup":0}
    email=st.session_state.user_email; docs=[]
    try:
        q=db.collection("sinyal_arsivi").where("user_email","==",email).limit(1000)
        for doc in q.stream():
            v=doc.to_dict() or {}
            if v.get("yon")=="ALIM": docs.append((doc.id,v))
    except Exception as e:
        izfin_hata_logla("gecmis_kayit_temizlik_okuma",e); return {"silinen":0,"yedeklenen":0,"grup":0}
    gruplar={}
    for doc_id,v in docs:
        ticker=str(v.get("ticker","")).strip().upper(); durum=str(v.get("durum","ACIK") or "ACIK").upper()
        if not ticker: continue
        if durum=="ACIK": key=("ACIK",ticker)
        else:
            t=pd.to_datetime(v.get("olusturma_zamani"),errors="coerce"); k=pd.to_datetime(v.get("kapanis_zamani"),errors="coerce")
            try: g=round(float(v.get("giris_fiyati",0) or 0),4)
            except Exception: g=0.0
            key=("KAPALI",ticker,t.floor("min").isoformat() if not pd.isna(t) else str(v.get("olusturma_zamani","")),k.floor("min").isoformat() if not pd.isna(k) else str(v.get("kapanis_zamani","")),g)
        gruplar.setdefault(key,[]).append((doc_id,v))
    silinen=yedeklenen=grup_sayisi=0; email_key=email.replace("@","_").replace(".","_")
    for key,grup in gruplar.items():
        if len(grup)<=1: continue
        grup_sayisi+=1; ticker=key[1]; keep_id=None
        if key[0]=="ACIK":
            # İlk alım tarihi/fiyatı kaybolmasın: açık grubun daima en eski belgesi korunur.
            keep_id=sorted(grup,key=lambda x:str(x[1].get("olusturma_zamani","")))[0][0]
        else:
            keep_id=sorted(grup,key=lambda x:sum(v is not None for v in x[1].values()),reverse=True)[0][0]
        for doc_id,v in grup:
            if doc_id==keep_id: continue
            try:
                backup_id=f"{doc_id}_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
                db.collection("sinyal_arsivi_temizlik_yedegi").document(backup_id).set({**v,"orijinal_doc_id":doc_id,"temizlik_zamani":datetime.now().isoformat(),"temizlik_nedeni":"gecmis_mukerrer_kayit","korunan_doc_id":keep_id})
                yedeklenen+=1; db.collection("sinyal_arsivi").document(doc_id).delete(); silinen+=1
            except Exception as e: izfin_hata_logla("gecmis_kayit_temizlik_silme",e,ticker)
        if key[0]=="ACIK":
            try:
                aktif_id=f"{email_key}_{ticker.replace('.', '_')}"; db.collection("aktif_sinyaller").document(aktif_id).set({"arsiv_doc_id":keep_id,"durum":"ACIK"},merge=True)
            except Exception as e: izfin_hata_logla("gecmis_kayit_temizlik_aktif_bag",e,ticker)
    return {"silinen":silinen,"yedeklenen":yedeklenen,"grup":grup_sayisi}

@st.cache_data(ttl=300, show_spinner=False)
def _performans_kayitlarini_getir_cached(email, limit=250, cache_epoch=0):
    """Firestore performans okumalarını 5 dakika önbelleğe alır.

    cache_epoch yalnızca yazma/temizlik sonrası aynı kullanıcı için önbelleği
    mantıksal olarak geçersiz kılmak amacıyla kullanılır.
    """
    if not db or not email:
        return []
    try:
        sorgu = (
            db.collection("sinyal_arsivi")
            .where("user_email", "==", email)
            .limit(limit)
        )
        kayitlar = []
        for doc in sorgu.stream():
            veri = doc.to_dict() or {}
            if veri.get("yon") != "ALIM":
                continue
            veri["doc_id"] = doc.id
            kayitlar.append(veri)
        kayitlar.sort(key=lambda x: x.get("olusturma_zamani", ""), reverse=True)
        return kayitlar
    except Exception as e:
        izfin_hata_logla("performans_firestore_okuma", e)
        return []


def performans_kayitlarini_getir(limit=250):
    if not db or not st.session_state.user_email:
        return []
    kayitlar = _performans_kayitlarini_getir_cached(
        st.session_state.user_email,
        limit=limit,
        cache_epoch=int(st.session_state.get("performans_cache_epoch", 0)),
    )
    return list(kayitlar)




def performans_cache_gecersiz_kil():
    try:
        st.session_state.performans_cache_epoch = int(
            st.session_state.get("performans_cache_epoch", 0)
        ) + 1
    except Exception:
        pass


def _guvenli_dict(deger):
    """Firestore/Pandas geçmiş kayıt alanını güvenli sözlüğe dönüştürür."""
    if isinstance(deger, dict):
        return deger
    # NaN, None, string, list vb. eski tipleri boş sözlük kabul et.
    return {}


def _guvenli_float(deger, varsayilan=np.nan):
    try:
        sonuc = float(deger)
        return sonuc if np.isfinite(sonuc) else varsayilan
    except Exception:
        return varsayilan


def performans_kayitlarini_tekillestir(kayitlar):
    """Firestore'daki eski mükerrer kayıtları ekranda güvenli biçimde birleştirir.

    Açık pozisyon:
      - ticker başına tek satır,
      - ilk alım tarihi ve ilk giriş fiyatı EN ESKİ kayıttan,
      - güncel sinyal/fiyat ve teknik alanlar EN YENİ kayıttan alınır.

    Kapalı pozisyon:
      - farklı alım dönemleri korunur,
      - yalnızca aynı ticker + aynı ilk alım zamanı/fiyat kombinasyonundaki
        eski teknik mükerrerler tek satıra indirilir.

    Firestore belgelerini silmez; yalnızca okuma/gösterim katmanını temizler.
    """
    if not kayitlar:
        return []

    df = pd.DataFrame(kayitlar).copy()
    if df.empty:
        return []

    for col in ["ticker", "durum", "yon"]:
        if col not in df.columns:
            df[col] = ""

    df["ticker"] = (
        df["ticker"].fillna("").astype(str).str.strip().str.upper()
    )
    df["durum"] = (
        df["durum"].fillna("ACIK").replace({"None": "ACIK", "": "ACIK"})
        .astype(str).str.upper()
    )
    df["_tarih"] = pd.to_datetime(df.get("olusturma_zamani"), errors="coerce")
    df["_guncel_tarih"] = pd.to_datetime(df.get("guncelleme_zamani"), errors="coerce")

    # --------------------------------------------------------------
    # AÇIKLAR: ticker başına tek dönem
    # --------------------------------------------------------------
    acik = df[df["durum"].eq("ACIK") & df["ticker"].ne("")].copy()
    acik_birlesik = []

    for ticker, grup in acik.groupby("ticker", sort=False):
        grup = grup.sort_values(
            ["_tarih", "_guncel_tarih"], ascending=[True, True], na_position="last"
        )
        ilk = grup.iloc[0].to_dict()
        son = grup.sort_values(
            ["_guncel_tarih", "_tarih"], ascending=[False, False], na_position="last"
        ).iloc[0].to_dict()

        # İlk giriş kimliğini koru.
        birlesik = dict(son)
        for alan in [
            "doc_id", "olusturma_zamani", "giris_fiyati",
            "ilk_sinyal", "strategy_version",
            "ilk_hibrit_skor", "ilk_giris_kalitesi",
            "ilk_algoritma_guveni", "ilk_peg", "ilk_sektorel_fark",
            "ilk_stop", "ilk_tp1", "ilk_tp2", "ilk_tp3",
            "benchmark_ticker"
        ]:
            if alan in ilk:
                deger = ilk.get(alan)
                try:
                    gecerli = not pd.isna(deger)
                except Exception:
                    gecerli = deger is not None
                if gecerli:
                    birlesik[alan] = deger

        # Karne alanı yalnızca gerçekten sözlükse taşınır.
        birlesik["performans_ufuklari"] = _guvenli_dict(
            ilk.get("performans_ufuklari")
        )

        # Güncel getiri MUTLAKA ilk giriş fiyatından hesaplanır.
        try:
            giris = float(birlesik.get("giris_fiyati", 0) or 0)
            son_fiyat = float(son.get("son_fiyat", son.get("kapanis_fiyati", 0)) or 0)
            if giris > 0 and son_fiyat > 0:
                birlesik["son_fiyat"] = son_fiyat
                birlesik["getiri_yuzde"] = (son_fiyat / giris - 1.0) * 100.0
        except Exception:
            pass

        birlesik["durum"] = "ACIK"
        birlesik["_mukerrer_sayisi"] = int(len(grup))
        acik_birlesik.append(birlesik)

    # --------------------------------------------------------------
    # KAPALILAR: gerçek farklı dönemler korunur, teknik kopyalar elenir.
    # --------------------------------------------------------------
    kapali = df[df["durum"].eq("KAPALI") & df["ticker"].ne("")].copy()
    kapali_birlesik = []

    if not kapali.empty:
        # Dakika düzeyinde başlangıç + ilk fiyat, eski sürümlerde oluşmuş aynı
        # işlem kopyalarını ayırmak için yeterince güvenli bir parmak izidir.
        kapali["_ilk_dakika"] = kapali["_tarih"].dt.floor("min")
        giris_num = pd.to_numeric(kapali.get("giris_fiyati"), errors="coerce")
        kapali["_giris_anahtar"] = giris_num.round(6)

        for _, grup in kapali.groupby(
            ["ticker", "_ilk_dakika", "_giris_anahtar"], dropna=False, sort=False
        ):
            # En dolu / en güncel kapanış kaydını al.
            grup = grup.copy()
            grup["_doluluk"] = grup.notna().sum(axis=1)
            secilen = grup.sort_values(
                ["_doluluk", "_guncel_tarih"], ascending=[False, False], na_position="last"
            ).iloc[0].to_dict()
            secilen["_mukerrer_sayisi"] = int(len(grup))
            kapali_birlesik.append(secilen)

    birlesikler = acik_birlesik + kapali_birlesik
    for k in birlesikler:
        k.pop("_tarih", None)
        k.pop("_guncel_tarih", None)
        k.pop("_ilk_dakika", None)
        k.pop("_giris_anahtar", None)
        k.pop("_doluluk", None)

    birlesikler.sort(
        key=lambda x: str(x.get("olusturma_zamani", "")),
        reverse=True
    )
    return birlesikler


def performans_fiyatlarini_guncelle(kayitlar):
    if not db:
        return kayitlar
    guncellenen = []
    fiyat_cache = {}
    for kayit in kayitlar:
        ticker = kayit.get("ticker")
        if not ticker:
            continue
        if ticker not in fiyat_cache:
            try:
                q = finnhub_quote_cek(ticker)
                fiyat = float(q.get("c", 0)) if q else 0.0
                if fiyat <= 0:
                    intraday = intraday_veri_cek(ticker, interval="5m", period="1d")
                    if not intraday.empty:
                        fiyat = float(intraday["Close"].dropna().iloc[-1])
                fiyat_cache[ticker] = fiyat
            except Exception:
                fiyat_cache[ticker] = 0.0
        son_fiyat = fiyat_cache[ticker]
        giris = float(kayit.get("giris_fiyati", 0) or 0)
        yon = kayit.get("yon", "ALIM")
        if son_fiyat > 0 and giris > 0:
            ham = ((son_fiyat - giris) / giris) * 100
            getiri = ham if yon == "ALIM" else -ham
            kayit["son_fiyat"] = son_fiyat
            kayit["getiri_yuzde"] = getiri
            kayit["guncelleme_zamani"] = datetime.now().isoformat()
            try:
                db.collection("sinyal_arsivi").document(kayit["doc_id"]).set({
                    "son_fiyat": son_fiyat,
                    "getiri_yuzde": getiri,
                    "guncelleme_zamani": kayit["guncelleme_zamani"],
                }, merge=True)
            except Exception:
                pass
        guncellenen.append(kayit)
    return guncellenen



def _gunluk_kapanis_serisi(ticker, period="1y"):
    """Performans karnesi için temiz günlük kapanış serisi döndürür."""
    try:
        df = yf.download(
            ticker, period=period, interval="1d", progress=False,
            auto_adjust=True, threads=False, timeout=8
        )
        if df is None or df.empty:
            return pd.Series(dtype=float)
        if isinstance(df.columns, pd.MultiIndex):
            if "Close" in df.columns.get_level_values(0):
                close = df["Close"]
                if isinstance(close, pd.DataFrame):
                    close = close.iloc[:, 0]
            else:
                return pd.Series(dtype=float)
        else:
            if "Close" not in df.columns:
                return pd.Series(dtype=float)
            close = df["Close"]
        close = pd.to_numeric(close, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
        try:
            close.index = pd.to_datetime(close.index).tz_localize(None)
        except Exception:
            close.index = pd.to_datetime(close.index)
        return close.sort_index()
    except Exception:
        return pd.Series(dtype=float)


def performans_karnelerini_guncelle(kayitlar):
    """1/5/10/20/45 işlem günü sonuçlarını ve benchmark farkını kalıcılaştırır.

    İlk sinyal fiyatı/snapshot alanları değiştirilmez. Yeterli işlem günü oluşan
    ufuklar yalnızca bir kez yazılır; böylece geçmiş performans sonradan kaymaz.
    """
    if not db or not kayitlar:
        return kayitlar

    fiyat_seri_cache = {}
    simdi_iso = datetime.now().isoformat()

    for kayit in kayitlar:
        doc_id = kayit.get("doc_id")
        ticker = kayit.get("ticker")
        giris = float(kayit.get("giris_fiyati", 0) or 0)
        tarih = pd.to_datetime(kayit.get("olusturma_zamani"), errors="coerce")
        if not doc_id or not ticker or giris <= 0 or pd.isna(tarih):
            continue
        try:
            if getattr(tarih, "tzinfo", None) is not None:
                tarih = tarih.tz_localize(None)
        except Exception:
            pass

        benchmark = kayit.get("benchmark_ticker") or ("XU100.IS" if ticker.endswith(".IS") else "^IXIC")
        if ticker not in fiyat_seri_cache:
            fiyat_seri_cache[ticker] = _gunluk_kapanis_serisi(ticker)
        if benchmark not in fiyat_seri_cache:
            fiyat_seri_cache[benchmark] = _gunluk_kapanis_serisi(benchmark)

        seri = fiyat_seri_cache[ticker]
        bseri = fiyat_seri_cache[benchmark]
        if seri.empty:
            continue

        sonrasi = seri[seri.index.normalize() >= tarih.normalize()]
        if sonrasi.empty:
            continue

        # Sinyal gününden sonraki tamamlanmış işlem günlerini esas al.
        mevcut_ufuklar = dict(_guvenli_dict(kayit.get("performans_ufuklari")))
        guncel_ufuklar = dict(mevcut_ufuklar)

        # İlk 45 işlem günündeki maksimum olumlu/olumsuz hareket (entry fiyatına göre).
        pencere = sonrasi.iloc[:46]
        if not pencere.empty:
            getiriler = (pencere / giris - 1.0) * 100.0
            kayit["max_yukselis_45g"] = float(getiriler.max())
            kayit["max_dusus_45g"] = float(getiriler.min())

        # Benchmark başlangıcı: sinyal tarihi veya sonraki ilk işlem günü.
        b_sonrasi = bseri[bseri.index.normalize() >= tarih.normalize()] if not bseri.empty else pd.Series(dtype=float)
        b_baslangic = float(b_sonrasi.iloc[0]) if not b_sonrasi.empty else None

        for gun in PERFORMANS_UFUKLARI:
            key = str(gun)
            if key in mevcut_ufuklar:
                continue
            # 0 = sinyal günü/ilk uygun günlük bar; +N işlem günü için N. ileri bar.
            if len(sonrasi) <= gun:
                continue
            hedef_fiyat = float(sonrasi.iloc[gun])
            hisse_getiri = (hedef_fiyat / giris - 1.0) * 100.0

            benchmark_getiri = None
            alfa = None
            if b_baslangic and b_baslangic > 0 and len(b_sonrasi) > gun:
                b_hedef = float(b_sonrasi.iloc[gun])
                benchmark_getiri = (b_hedef / b_baslangic - 1.0) * 100.0
                alfa = hisse_getiri - benchmark_getiri

            guncel_ufuklar[key] = {
                "fiyat": round(hedef_fiyat, 6),
                "getiri": round(float(hisse_getiri), 4),
                "benchmark_getiri": round(float(benchmark_getiri), 4) if benchmark_getiri is not None else None,
                "alfa": round(float(alfa), 4) if alfa is not None else None,
                "olcum_tarihi": sonrasi.index[gun].isoformat(),
            }

        update = {
            "performans_ufuklari": guncel_ufuklar,
            "benchmark_ticker": benchmark,
            "karnenin_son_guncellemesi": simdi_iso,
        }
        if "max_yukselis_45g" in kayit:
            update["max_yukselis_45g"] = kayit["max_yukselis_45g"]
            update["max_dusus_45g"] = kayit["max_dusus_45g"]

        try:
            db.collection("sinyal_arsivi").document(doc_id).set(update, merge=True)
            kayit.update(update)
        except Exception:
            pass

    return kayitlar


def performans_karnesi_ozeti(kayitlar, gun=20):
    """Seçilen işlem günü ufku için toplu IZFIN karnesini hesaplar."""
    # Eski Firestore kopyalarının karnede aynı dönemi birkaç kez saymasını önle.
    kayitlar = performans_kayitlarini_tekillestir(kayitlar)
    satirlar = []
    key = str(gun)
    gorulen_donemler = set()
    for k in kayitlar:
        ufuklar = _guvenli_dict(k.get("performans_ufuklari"))
        ufuk = _guvenli_dict(ufuklar.get(key))
        getiri = _guvenli_float(ufuk.get("getiri"))
        if not np.isfinite(getiri):
            continue

        # Aynı hisse + aynı ilk alım dönemi karnede yalnızca bir kez sayılır.
        tarih_raw = str(k.get("olusturma_zamani", ""))
        try:
            tarih_anahtar = pd.to_datetime(tarih_raw, errors="coerce")
            if pd.isna(tarih_anahtar):
                tarih_anahtar = tarih_raw
            else:
                tarih_anahtar = tarih_anahtar.floor("min").isoformat()
        except Exception:
            tarih_anahtar = tarih_raw
        donem_anahtar = (
            str(k.get("ticker", "")).upper(),
            str(tarih_anahtar),
            round(_guvenli_float(k.get("giris_fiyati"), 0.0), 6),
        )
        if donem_anahtar in gorulen_donemler:
            continue
        gorulen_donemler.add(donem_anahtar)

        ilk_sinyal = k.get("ilk_sinyal") or k.get("sinyal") or "Kayıtlı alım"
        strateji_surumu = k.get("strategy_version") or ""
        ilk_hibrit = k.get("ilk_hibrit_skor")
        if ilk_hibrit is None:
            ilk_hibrit = k.get("hibrit_skor")
        ilk_giris = k.get("ilk_giris_kalitesi")
        if ilk_giris is None:
            ilk_giris = k.get("tetik_puani")

        satirlar.append({
            "ticker": k.get("ticker"),
            "sinyal_tarihi": pd.to_datetime(k.get("olusturma_zamani"), errors="coerce"),
            "sinyal": ilk_sinyal,
            "strategy_version": strateji_surumu,
            "hibrit_skor": ilk_hibrit,
            "giris_kalitesi": ilk_giris,
            "peg": k.get("ilk_peg"),
            "getiri": getiri,
            "benchmark_getiri": _guvenli_float(ufuk.get("benchmark_getiri")),
            "alfa": _guvenli_float(ufuk.get("alfa")),
            "max_dusus": _guvenli_float(k.get("max_dusus_45g")),
        })
    return pd.DataFrame(satirlar)

def opsiyon_projeksiyonu_hesapla(panel, gun=45):
    """ATR + tarihsel volatilite tabanlı karma fiyat projeksiyonu.

    Bu fonksiyon gerçek opsiyon zinciri veya implied volatility kullanmaz. ATR son
    fiyat aralıklarını, HV ise günlük getirilerin dağılımını temsil eder.
    """
    fiyat = float(panel.get("fiyat", 0) or 0)
    atr = float(panel.get("atr", 0) or 0)
    hv20 = float(panel.get("hv20", 0) or 0)
    hv60 = float(panel.get("hv60", hv20) or hv20)
    if fiyat <= 0:
        return None

    # ATR modeli: günlük gerçek fiyat aralığını zamanın kareköküyle ölçekler.
    atr_gunluk_oran = (atr / fiyat) if atr > 0 else 0.02
    atr_gunluk_oran = min(max(atr_gunluk_oran, 0.003), 0.15)
    atr_hareket = fiyat * atr_gunluk_oran * math.sqrt(gun)

    # Tarihsel volatilite modeli: yıllıklandırılmış sigma -> seçilen gün sayısı.
    if hv20 <= 0:
        hv20 = atr_gunluk_oran * math.sqrt(252)
    if hv60 <= 0:
        hv60 = hv20
    hv20 = min(max(hv20, 0.05), 2.50)
    hv60 = min(max(hv60, 0.05), 2.50)
    hv_karma = (0.65 * hv20) + (0.35 * hv60)
    volatilite_hareket = fiyat * hv_karma * math.sqrt(gun / 252)

    # Modeller birbirine yakınsa eşit ağırlık; ayrışma büyürse daha ihtiyatlı
    # biçimde büyük tahmine biraz daha fazla ağırlık verilir.
    kucuk = max(min(atr_hareket, volatilite_hareket), 1e-9)
    uyum_orani = max(atr_hareket, volatilite_hareket) / kucuk
    if uyum_orani <= 1.20:
        atr_agirlik, vol_agirlik = 0.50, 0.50
    elif atr_hareket > volatilite_hareket:
        atr_agirlik, vol_agirlik = 0.60, 0.40
    else:
        atr_agirlik, vol_agirlik = 0.40, 0.60

    karma_hareket = (atr_hareket * atr_agirlik) + (volatilite_hareket * vol_agirlik)

    # Güven skoru bir olasılık değildir; veri tutarlılığı ve gösterge teyidini
    # 0-100 arasında özetleyen karar destek puanıdır.
    model_uyumu = max(0.0, 1.0 - abs(atr_hareket - volatilite_hareket) / max(karma_hareket, 1e-9))
    veri_guveni = 1.0 if panel.get("veri_kaynagi") else 0.75
    trend_teyidi = 0.0
    fiyat_v = fiyat
    ema21 = float(panel.get("ema21", fiyat_v) or fiyat_v)
    ema50 = float(panel.get("ema50", fiyat_v) or fiyat_v)
    sma200 = float(panel.get("sma200", fiyat_v) or fiyat_v)
    macd = float(panel.get("macd", 0) or 0)
    macd_signal = float(panel.get("macd_signal", 0) or 0)
    rsi = float(panel.get("rsi", 50) or 50)
    trend_teyidi += 0.25 if fiyat_v > ema21 else 0.0
    trend_teyidi += 0.25 if ema21 > ema50 else 0.0
    trend_teyidi += 0.25 if fiyat_v > sma200 else 0.0
    trend_teyidi += 0.25 if macd > macd_signal and 40 <= rsi <= 70 else 0.0
    guven_skoru = int(round(min(95, max(45, 45 + 30 * model_uyumu + 10 * veri_guveni + 10 * trend_teyidi))))

    return {
        "gun": gun,
        "fiyat": fiyat,
        "atr_hareket": atr_hareket,
        "atr_yuzde": (atr_hareket / fiyat) * 100,
        "volatilite_hareket": volatilite_hareket,
        "volatilite_yuzde": (volatilite_hareket / fiyat) * 100,
        "hv20": hv20,
        "hv60": hv60,
        "hv_karma": hv_karma,
        "karma_hareket": karma_hareket,
        "karma_yuzde": (karma_hareket / fiyat) * 100,
        "guven_skoru": guven_skoru,
        "model_uyumu": model_uyumu,
        "alt_1s": max(0, fiyat - karma_hareket),
        "ust_1s": fiyat + karma_hareket,
        "alt_2s": max(0, fiyat - 2 * karma_hareket),
        "ust_2s": fiyat + 2 * karma_hareket,
    }

# --- UYGULAMA OTURUM DURUMU VARSAYILANLARI ---
# Streamlit her yeniden çalıştırmada bu alanları korur; ilk çalıştırmada ise
# eksik anahtarların AttributeError üretmesini engeller.
_SESSION_DEFAULTS = {
    "tarama_durumu": False,
    "sonuclar": [],
    "sozlu_analizler": {},
    "teknik_paneller": {},
    "performans_kayitlari": [],
    "performans_mesaji": "",
    "custom_tickers": VARSAYILAN_TICKERS.copy(),
    "basarisiz_taramalar": [],
    "boga_sayisi": 0,
    "alim_firsati": 0,
    "aktif_profil": "Kendi Listem",
    "secilen_varliklar": VARSAYILAN_TICKERS.copy(),
    "kullanici_listesi_yuklendi": False,
    "taramada_hatalar": [],
    "performans_cache_epoch": 0,
}
for _key, _default in _SESSION_DEFAULTS.items():
    if _key not in st.session_state:
        st.session_state[_key] = _default.copy() if hasattr(_default, "copy") else _default

# Kullanıcının Firebase'de kayıtlı özel listesini her oturumda yalnızca bir kez yükle.
# v1.7.13: Eski e-posta bazlı listeyi UID belgesi oluşmuş olsa bile güvenli biçimde kurtarır.
# Eski belge ASLA silinmez; yalnızca yeni UID belgesine kopyalanır/birleştirilir.
if st.session_state.user_email and db and not st.session_state.kullanici_listesi_yuklendi:
    try:
        _doc_id = _kullanici_liste_doc_id()
        _email_id = str(st.session_state.user_email or "").strip().lower()
        _uid_doc = db.collection("kullanici_listeleri").document(_doc_id).get()
        _legacy_doc = None
        if _email_id and _email_id != _doc_id:
            try:
                _legacy_doc = db.collection("kullanici_listeleri").document(_email_id).get()
            except Exception:
                _legacy_doc = None

        _uid_data = (_uid_doc.to_dict() or {}) if _uid_doc.exists else {}
        _legacy_data = (_legacy_doc.to_dict() or {}) if (_legacy_doc is not None and _legacy_doc.exists) else {}

        _uid_ticks = [
            str(x).strip().upper()
            for x in (_uid_data.get("tickers") or [])
            if str(x).strip()
        ]
        _legacy_ticks = [
            str(x).strip().upper()
            for x in (_legacy_data.get("tickers") or [])
            if str(x).strip()
        ]

        _varsayilan_set = set(str(x).strip().upper() for x in VARSAYILAN_TICKERS)
        _uid_set = set(_uid_ticks)
        _legacy_set = set(_legacy_ticks)

        # UID belgesi yoksa legacy doğrudan taşınır.
        # UID belgesi yalnızca varsayılanlardan oluşuyorsa ama legacy daha zenginse,
        # eski kişisel listenin üstüne yazılmış olma ihtimaline karşı legacy esas alınır.
        # Her iki tarafta gerçek kişisel eklemeler varsa kayıp olmaması için union yapılır.
        _kurtarma_gerekli = False
        if _legacy_ticks:
            if not _uid_doc.exists or not _uid_ticks:
                _final_ticks = _legacy_ticks
                _kurtarma_gerekli = True
            elif _uid_set.issubset(_varsayilan_set) and not _legacy_set.issubset(_varsayilan_set):
                _final_ticks = list(dict.fromkeys(_legacy_ticks + _uid_ticks))
                _kurtarma_gerekli = True
            else:
                # İki listede de kişisel içerik varsa güvenli birleşim.
                _final_ticks = list(dict.fromkeys(_uid_ticks + _legacy_ticks))
                if set(_final_ticks) != _uid_set:
                    _kurtarma_gerekli = True
        else:
            _final_ticks = _uid_ticks

        if not _final_ticks:
            _final_ticks = VARSAYILAN_TICKERS.copy()

        st.session_state.custom_tickers = _final_ticks

        if _kurtarma_gerekli and st.session_state.get("user_uid"):
            db.collection("kullanici_listeleri").document(_doc_id).set({
                "uid": st.session_state.user_uid,
                "email": st.session_state.user_email,
                "tickers": _final_ticks,
                "legacy_kurtarildi": True,
                "guncelleme_zamani": datetime.now().isoformat(),
            }, merge=True)
            st.session_state["liste_kurtarma_mesaji"] = True

        if st.session_state.aktif_profil == "Kendi Listem":
            st.session_state.secilen_varliklar = st.session_state.custom_tickers.copy()

        st.session_state.kullanici_listesi_yuklendi = True

    except Exception as _liste_hatasi:
        st.warning(f"Kayıtlı listeniz şu anda yüklenemedi: {_liste_hatasi}")

def kullanici_listesini_kaydet():
    if not db or not st.session_state.get("user_email"):
        return
    try:
        db.collection("kullanici_listeleri").document(_kullanici_liste_doc_id()).set({"uid": st.session_state.get("user_uid"),"email": st.session_state.user_email,"tickers": list(dict.fromkeys(st.session_state.custom_tickers)),"guncelleme_zamani": datetime.now().isoformat()}, merge=True)
    except Exception as e:
        izfin_hata_logla("kullanici_listesi_yaz", e)

@st.cache_data(ttl=90, show_spinner=False)
def hisse_onerileri_getir(arama):
    """
    Canlı sembol/şirket araması.
    Kullanıcı birkaç harf yazdığında Yahoo Finance Search üzerinden dünya piyasalarını arar.
    Finnhub ikinci kaynak, IZFIN yerel evreni ise son güvenli fallback'tir.
    """
    q = str(arama or "").strip()
    if len(q) < 1:
        return []

    q_up = q.upper()
    sonuc = []
    seen = set()

    def _ekle(symbol, name="", exchange="", quote_type=""):
        symbol = str(symbol or "").strip().upper()
        if not symbol or symbol in seen:
            return
        seen.add(symbol)
        sonuc.append({
            "symbol": symbol,
            "name": str(name or "").strip(),
            "exchange": str(exchange or "").strip(),
            "quote_type": str(quote_type or "").strip(),
        })

    # 1) Yahoo Finance: şirket adı + sembol + fuzzy search.
    try:
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json,text/plain,*/*",
        }
        r = session.get(
            "https://query2.finance.yahoo.com/v1/finance/search",
            params={
                "q": q,
                "quotesCount": 20,
                "newsCount": 0,
                "listsCount": 0,
                "enableFuzzyQuery": "true",
                "quotesQueryId": "tss_match_phrase_query",
                "multiQuoteQueryId": "multi_quote_single_token_query",
            },
            headers=headers,
            timeout=6,
        )
        if r.ok:
            payload = r.json() or {}
            for x in payload.get("quotes", []) or []:
                qt = str(x.get("quoteType") or "").upper()
                # Kullanıcı hisse ekliyor: equity/ETF ağırlıklı sonuçlar.
                if qt not in {"EQUITY", "ETF", "MUTUALFUND", "INDEX"}:
                    continue
                _ekle(
                    x.get("symbol"),
                    x.get("shortname") or x.get("longname") or x.get("name"),
                    x.get("exchDisp") or x.get("exchange"),
                    qt,
                )
    except Exception:
        pass

    # 2) Finnhub: Yahoo az sonuç verdiyse tamamla.
    if len(sonuc) < 8 and FINNHUB_API_KEY:
        try:
            fh = _finnhub_get("search", {"q": q}, timeout=5, max_retry=1) or {}
            for x in fh.get("result", []) or []:
                typ = str(x.get("type") or "").upper()
                symbol = str(x.get("symbol") or "").strip()
                if not symbol:
                    continue
                # COMMON STOCK başta olmak üzere yatırım yapılabilir sembolleri göster.
                if typ and typ not in {
                    "COMMON STOCK", "ADR", "ETP", "REIT", "PREFERRED STOCK",
                    "UNIT", "CLOSED-END FUND"
                }:
                    continue
                _ekle(
                    symbol,
                    x.get("description"),
                    x.get("displaySymbol"),
                    typ,
                )
        except Exception:
            pass

    # 3) Yerel evren fallback + yazılan sembolü kaybetmeme.
    try:
        local_universe = sorted(set(BIST_100 + ABD_HİSSELERİ + st.session_state.get("custom_tickers", [])))
    except Exception:
        local_universe = []

    local_matches = [
        s for s in local_universe
        if q_up in str(s).upper()
    ]
    for s in local_matches:
        _ekle(
            s,
            "IZFIN evreni",
            "BIST" if str(s).upper().endswith(".IS") else "US",
            "EQUITY",
        )

    # Tam sembol olabilecek girişte kullanıcı manuel eklemeye mecbur kalmasın.
    if q.replace(".", "").replace("-", "").isalnum() and len(q) <= 15:
        if not any(x["symbol"] == q_up for x in sonuc):
            _ekle(q_up, "Sembol olarak ekle", "", "SYMBOL")

    return sonuc[:15]

def get_preset_options():
    return {"Kendi Listem": st.session_state.custom_tickers, "BIST 30": BIST_30, "BIST 100": BIST_100, "ABD Büyük Teknoloji": ABD_HİSSELERİ}

preset_options = get_preset_options()
tum_varliklar_havuzu = list(set([h for lst in preset_options.values() for h in lst]))

if "aktif_profil" not in st.session_state: st.session_state.aktif_profil = "Kendi Listem"
if "secilen_varliklar" not in st.session_state: st.session_state.secilen_varliklar = st.session_state.custom_tickers.copy()

def profil_degisti():
    p = st.session_state.profil_selectbox_key
    st.session_state.aktif_profil = p
    st.session_state.secilen_varliklar = preset_options[p].copy()

def hisse_ekle_callback():
    """Manuel hisse ekleme + kullanıcıya net başarı/hata geri bildirimi."""
    try:
        raw = str(st.session_state.get("ek_hisse_input_field", "") or "").strip()
        symbol = raw.upper()

        if not raw:
            st.session_state["liste_islem_mesaji"] = ("error", "Hisse eklenemedi: Lütfen önce bir hisse sembolü yazın.")
            return

        if len(symbol) > 20:
            st.session_state["liste_islem_mesaji"] = ("error", f"{symbol} eklenemedi: Sembol beklenenden uzun görünüyor.")
            return

        if symbol in st.session_state.custom_tickers:
            st.session_state["liste_islem_mesaji"] = ("warning", f"{symbol} zaten kişisel listenizde bulunuyor.")
            return

        # Önce session listesine ekle, ardından Firebase'e kaydet.
        eski_liste = st.session_state.custom_tickers.copy()
        st.session_state.custom_tickers.append(symbol)

        try:
            kullanici_listesini_kaydet()
        except Exception as firebase_hatasi:
            # Kalıcı kayıt başarısızsa bellekteki eklemeyi de geri al.
            st.session_state.custom_tickers = eski_liste
            st.session_state["liste_islem_mesaji"] = (
                "error",
                f"{symbol} listeye eklenemedi: Firebase kaydı tamamlanamadı. {firebase_hatasi}"
            )
            return

        st.session_state.aktif_profil = "Kendi Listem"
        st.session_state.secilen_varliklar = st.session_state.custom_tickers.copy()
        st.session_state["ek_hisse_input_field"] = ""
        st.session_state["liste_islem_mesaji"] = (
            "success",
            f"{symbol} kişisel listenize başarıyla eklendi."
        )

    except Exception as hata:
        st.session_state["liste_islem_mesaji"] = (
            "error",
            f"Hisse listeye eklenemedi: {hata}"
        )

def hisse_sil_callback():
    input_val = st.session_state.sil_hisse_input_field
    if input_val and input_val.strip():
        for h in [x.strip().upper() for x in input_val.replace(",", " ").split() if x.strip()]:
            if h in st.session_state.custom_tickers: st.session_state.custom_tickers.remove(h)
        kullanici_listesini_kaydet()
        st.session_state.aktif_profil = "Kendi Listem"
        st.session_state.secilen_varliklar = st.session_state.custom_tickers.copy()
        st.session_state.sil_hisse_input_field = ""


# --- IZFIN SIGNATURE UI ---
IZFIN_LOGO_B64 = "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"

def izfin_brand_html():
    return f"""
    <div class="iz-brand">
      <img src="data:image/png;base64,{IZFIN_LOGO_B64}" alt="IZFIN sembolü">
      <div><div class="iz-brand-name">IZFIN</div><div class="iz-brand-tag">ANALYZE • PREDICT • INVEST</div></div>
    </div>"""

@st.cache_data(ttl=60, show_spinner=False)
def izfin_piyasa_bandi_verisi():
    """Üst piyasa bandını 1 dk gün içi veriden üretir; günlük veri yalnızca fallback/ref close içindir.

    Bu bir borsa-direct-feed değildir. Yahoo tarafında enstrümana göre gecikme olabileceği için
    her kutuda veri kaynağı ve tüm bantta tazelik durumu ayrıca gösterilir.
    """
    semboller = {
        "BIST 100":"XU100.IS", "S&P 500":"^GSPC", "NASDAQ 100":"^NDX",
        "DOW JONES":"^DJI", "VIX":"^VIX", "ONS ALTIN":"GC=F", "USD/TRY":"TRY=X"
    }
    ticker_list = list(semboller.values())
    try:
        intra_all = yf.download(
            ticker_list, period="1d", interval="1m", group_by="ticker",
            progress=False, threads=True, prepost=True, auto_adjust=True, timeout=8
        )
    except Exception as e:
        izfin_hata_logla("signature_piyasa_bandi_1m", e)
        intra_all = pd.DataFrame()
    try:
        daily_all = yf.download(
            ticker_list, period="7d", interval="1d", group_by="ticker",
            progress=False, threads=True, auto_adjust=True, timeout=8
        )
    except Exception as e:
        izfin_hata_logla("signature_piyasa_bandi_daily", e)
        daily_all = pd.DataFrame()

    cikti = []
    tazelik_saniye = []
    simdi_utc = pd.Timestamp.now(tz="UTC")
    for ad, sembol in semboller.items():
        son = onceki = deg = None
        kaynak = "Yahoo günlük fallback"
        son_zaman = None
        try:
            intra = toplu_veriden_ticker_ayir(intra_all, sembol, len(ticker_list))
            if not intra.empty and "Close" in intra.columns:
                ic = pd.to_numeric(intra["Close"], errors="coerce").dropna()
                if not ic.empty:
                    son = float(ic.iloc[-1])
                    son_zaman = pd.Timestamp(ic.index[-1])
                    if son_zaman.tzinfo is None:
                        son_zaman = son_zaman.tz_localize("UTC")
                    else:
                        son_zaman = son_zaman.tz_convert("UTC")
                    tazelik_saniye.append(max(0.0, (simdi_utc-son_zaman).total_seconds()))
                    kaynak = "Yahoo 1 dk"
            daily = toplu_veriden_ticker_ayir(daily_all, sembol, len(ticker_list))
            if not daily.empty and "Close" in daily.columns:
                dc = pd.to_numeric(daily["Close"], errors="coerce").dropna()
                if not dc.empty:
                    # Intraday varsa bugünkü kısmi daily satırını referans olarak kullanma.
                    if son_zaman is not None and len(dc) >= 2 and pd.Timestamp(dc.index[-1]).date() == son_zaman.date():
                        onceki = float(dc.iloc[-2])
                    elif len(dc) >= 1:
                        onceki = float(dc.iloc[-1])
                    if son is None:
                        son = float(dc.iloc[-1])
                        onceki = float(dc.iloc[-2]) if len(dc) >= 2 else onceki
            if son is not None and onceki not in (None, 0):
                deg = ((son/onceki)-1.0)*100.0
        except Exception as e:
            izfin_hata_logla("signature_piyasa_bandi_ticker", e, sembol)
        cikti.append({"ad":ad,"fiyat":son,"deg":deg,"kaynak":kaynak,"ts":son_zaman})

    medyan_gecikme = float(np.median(tazelik_saniye)) if tazelik_saniye else None
    if medyan_gecikme is None:
        durum = "VERİ KONTROL"
    elif medyan_gecikme <= 180:
        durum = "YAKIN CANLI"
    elif medyan_gecikme <= 1200:
        durum = "GECİKMELİ"
    else:
        durum = "PİYASA KAPALI / ESKİ"
    return {"items":cikti,"durum":durum,"gecikme_sn":medyan_gecikme,"yerel_saat":datetime.now(ZoneInfo("Europe/Istanbul")).strftime("%H:%M:%S")}

def _iz_num(v, yuzde=False):
    try:
        if v is None or not np.isfinite(float(v)):
            return "—"
        v = float(v)
    except Exception:
        return "—"
    if yuzde:
        return f"%{v:+.2f}"
    if abs(v) >= 10000: return f"{v:,.0f}"
    if abs(v) >= 1000: return f"{v:,.2f}"
    if abs(v) >= 10: return f"{v:,.2f}"
    return f"{v:,.3f}"

def izfin_market_bar_html(bant_paketi):
    items = bant_paketi.get("items", []) if isinstance(bant_paketi, dict) else (bant_paketi or [])
    durum = bant_paketi.get("durum", "VERİ KONTROL") if isinstance(bant_paketi, dict) else "VERİ KONTROL"
    gec = bant_paketi.get("gecikme_sn") if isinstance(bant_paketi, dict) else None
    saat = bant_paketi.get("yerel_saat", "—") if isinstance(bant_paketi, dict) else "—"
    gec_txt = "—" if gec is None else (f"~{int(gec)} sn" if gec < 120 else f"~{int(gec//60)} dk")
    kutular = []
    for x in items:
        deg = x.get("deg")
        cls = "iz-up" if deg is not None and deg >= 0 else "iz-down"
        ok = "▲" if deg is not None and deg >= 0 else "▼"
        kutular.append(f'''<div class="iz-ticker"><div class="n">{x['ad']}</div><div class="v">{_iz_num(x.get('fiyat'))}</div><div class="{cls}" style="font-size:10px;margin-top:2px">{ok} {_iz_num(deg,True)}</div><div style="font-size:7px;color:#526f84;margin-top:3px">{x.get('kaynak','')}</div></div>''')
    return f'''<div class="iz-live-shell"><div class="iz-live-status"><div class="s1">PİYASALAR</div><div class="s2">● {durum}</div><div class="s3">Tazelik {gec_txt} · {saat}</div></div><div class="iz-livebar">{''.join(kutular)}</div></div>'''

def _iz_panel_metrics():
    paneller = list((st.session_state.get("teknik_paneller") or {}).values())
    if not paneller:
        bant = izfin_piyasa_bandi_verisi().get("items", [])
        degler = [float(x["deg"]) for x in bant if x.get("deg") is not None and np.isfinite(float(x["deg"])) and x["ad"] != "VIX"]
        ort = np.mean(degler) if degler else 0.0
        pulse = int(np.clip(round(50 + ort * 8), 15, 85))
        return pulse, pulse, int(np.clip(pulse-4,0,100)), int(np.clip(pulse-2,0,100)), 50, "PİYASA VERİSİ"
    trend = np.mean([1 if float(p.get("fiyat",0)) > float(p.get("sma200",float("inf"))) else 0 for p in paneller]) * 100
    momentum = np.mean([1 if float(p.get("macd",0)) > float(p.get("macd_signal",0)) else 0 for p in paneller]) * 100
    flow = np.mean([1 if float(p.get("cmf",0)) > 0 else 0 for p in paneller]) * 100
    risk_map = {"DÜŞÜK":25,"ORTA":50,"YÜKSEK":75,"ÇOK YÜKSEK":90}
    risks = [risk_map.get(str(p.get("risk_seviyesi","ORTA")).upper(),50) for p in paneller]
    risk = float(np.mean(risks)) if risks else 50
    pulse = int(round(np.clip(.34*trend + .27*momentum + .24*flow + .15*(100-risk),0,100)))
    return pulse,int(round(trend)),int(round(momentum)),int(round(flow)),int(round(risk)),"IZFIN TARAMASI"

def _iz_pulse_label(p):
    if p >= 72: return "GÜÇLÜ POZİTİF"
    if p >= 60: return "POZİTİF"
    if p >= 45: return "DENGELİ"
    if p >= 32: return "TEMKİNLİ"
    return "RİSKLİ"

def _iz_detail_href(ticker):
    ticker = str(ticker or "").strip().upper()
    return "?" + urlencode({"izfin_detail": ticker}) + "#izfin-detail-anchor"


def _iz_heatmap_items(max_n=16):
    sonuclar = st.session_state.get("sonuclar") or []
    paneller = st.session_state.get("teknik_paneller") or {}
    items = []
    for r in sonuclar:
        t = str(r.get("Varlık",""))
        p = paneller.get(t,{})
        skor = float(p.get("cezali_skor", p.get("nihai_skor",50)) or 50)
        guven = float(p.get("guven_skoru",50) or 50)
        d = float(p.get("gunluk_degisim",0) or 0)
        items.append((skor,guven,t,d))
    items.sort(reverse=True)
    return items[:max_n]

def _iz_heat_color(skor):
    if skor >= 78: return "background:linear-gradient(145deg,#0b684e,#075743)"
    if skor >= 66: return "background:linear-gradient(145deg,#0b514a,#0a3f40)"
    if skor >= 55: return "background:linear-gradient(145deg,#123b45,#102f3b)"
    if skor >= 45: return "background:linear-gradient(145deg,#263842,#1e2d37)"
    return "background:linear-gradient(145deg,#5b202a,#421b23)"

def izfin_dashboard_html():
    pulse,trend,momentum,flow,risk,kaynak = _iz_panel_metrics()
    items = _iz_heatmap_items(max_n=20)
    if items:
        parts = []
        for s,g,t,d in items:
            _href = _iz_detail_href(t)
            _safe_t = html.escape(str(t))
            parts.append(
                f'<a class="iz-heat iz-home-stock-link" href="{html.escape(_href, quote=True)}" '
                f'title="{_safe_t} detay analizine git" '
                f'style="{_iz_heat_color(s)};box-shadow:inset 0 0 0 {max(1,int(g/30))}px rgba(38,238,220,.13)">'
                f'<strong>{_safe_t}</strong><span>IZ {int(s)} · Güven {int(g)}%</span>'
                f'<span style="display:block;color:{"#31e59c" if d>=0 else "#ff6b78"};margin-top:2px">{d:+.2f}%</span>'
                f'<span class="iz-open-detail">Detayı aç ↗</span></a>'
            )
        heat = ''.join(parts)
    else:
        heat = '<div style="grid-column:1/-1;padding:34px 15px;text-align:center;color:#7891a5;border:1px dashed #1a4059;border-radius:11px"><b style="color:#b7c9d6">İlk Akıllı Tarama bekleniyor</b><br><span style="font-size:10px">Tarama sonrası renk = IZFIN skoru, çerçeve = algoritma güveni olacak.</span></div>'
    trend_lbl = "GÜÇLÜ" if trend >= 70 else "İYİ" if trend >= 55 else "KARIŞIK"
    mom_lbl = "GÜÇLÜ" if momentum >= 70 else "İYİ" if momentum >= 55 else "KARIŞIK"
    flow_lbl = "POZİTİF" if flow >= 60 else "DENGELİ" if flow >= 45 else "ZAYIF"
    risk_lbl = "DÜŞÜK" if risk < 40 else "ORTA" if risk < 65 else "YÜKSEK"
    return f"""
    <div class="iz-hero"><div class="iz-section-label">IZFIN SIGNATURE COMMAND CENTER</div><h1>IZFIN Piyasa Merkezi</h1><p>Piyasanın nabzını gör, fırsatı tara, kararın gerekçesini incele ve sonucu ölç.</p></div>
    <div class="iz-dashboard">
      <div class="iz-card">
        <div class="iz-card-head"><div><div class="iz-card-title" style="margin:0">IZFIN PİYASA NABZI</div><div class="iz-card-kicker">{kaynak}</div></div><span class="iz-badge wait">{_iz_pulse_label(pulse)}</span></div>
        <div class="iz-pulse">
          <div class="iz-gauge" style="--pulse:{pulse}%"><div class="iz-gauge-content"><div class="iz-gauge-num">{pulse}<span style="font-size:12px;color:#7890a3">/100</span></div><div class="iz-gauge-label">{_iz_pulse_label(pulse)}</div></div></div>
          <div><div class="iz-pulse-copy">Trend, momentum, para akışı ve risk tek çerçevede okunur. Tarama sonrası nabız doğrudan IZFIN teknik motorunun analiz ettiği varlıklardan hesaplanır.</div>
          <div class="iz-components">
            <div class="iz-comp"><div class="iz-comp-name">TREND</div><div class="iz-comp-val">{trend}</div><div class="iz-comp-sub">{trend_lbl}</div></div>
            <div class="iz-comp"><div class="iz-comp-name">MOMENTUM</div><div class="iz-comp-val">{momentum}</div><div class="iz-comp-sub">{mom_lbl}</div></div>
            <div class="iz-comp"><div class="iz-comp-name">PARA AKIŞI</div><div class="iz-comp-val">{flow}</div><div class="iz-comp-sub">{flow_lbl}</div></div>
            <div class="iz-comp"><div class="iz-comp-name">RİSK</div><div class="iz-comp-val">{risk}</div><div class="iz-comp-sub" style="color:#f2b94d">{risk_lbl}</div></div>
          </div></div>
        </div>
      </div>
      <div class="iz-card">
        <div class="iz-card-head"><div><div class="iz-card-title" style="margin:0">IZFIN FIRSAT HARİTASI</div><div class="iz-card-kicker">RENK = SKOR · ÇERÇEVE = GÜVEN</div></div><span style="font-size:9px;color:#4ecfe0">SIGNATURE MAP</span></div>
        <div class="iz-heat-grid">{heat}</div>
      </div>
    </div>"""

def _iz_badge_class(s):
    u = str(s).upper()
    if "GÜÇLÜ AL" in u or ("AL" in u and "ERKEN" not in u): return "buy"
    if "ERKEN" in u: return "early"
    if "TEYİT" in u or "İZLE" in u: return "wait"
    return "risk"

def izfin_top_signals_html(max_n=7):
    sonuclar = st.session_state.get("sonuclar") or []
    paneller = st.session_state.get("teknik_paneller") or {}
    sirali = sorted(sonuclar, key=lambda r: float(paneller.get(str(r.get("Varlık","")),{}).get("cezali_skor",0) or 0), reverse=True)[:max_n]
    rows = []
    for r in sirali:
        t = str(r.get("Varlık","")); p = paneller.get(t,{})
        sin = str(r.get("Nihai Sinyal","—"))
        skor = int(float(p.get("cezali_skor",0) or 0)); g = int(float(p.get("guven_skoru",50) or 50))
        fiyat = r.get("Fiyat","—"); risk = p.get("risk_seviyesi",r.get("Risk","—")); mtf = int(float(p.get("mtf_uyum",50) or 50))
        _href = _iz_detail_href(t)
        _safe_t = html.escape(t)
        rows.append(
            f'<tr class="iz-click-row">'
            f'<td><a class="iz-ticker-link" href="{html.escape(_href, quote=True)}" title="{_safe_t} detay analizine git"><b>{_safe_t}</b><span>↗</span></a></td>'
            f'<td>{fiyat}</td><td><span class="iz-badge {_iz_badge_class(sin)}">{sin}</span></td>'
            f'<td><b style="color:#20e69a">{skor}</b></td><td><div class="iz-ring" style="--g:{g}"><span>{g}%</span></div></td>'
            f'<td>{mtf}%</td><td>{risk}</td></tr>'
        )
    if not rows:
        return '<div class="iz-signals"><div class="iz-card-title">ÖNE ÇIKAN IZFIN SİNYALLERİ</div><div style="color:#7891a5;padding:18px 0">Derin Tarama çalıştırıldığında en yüksek skorlu sinyaller burada özetlenecek.</div></div>'
    return '<div class="iz-signals"><div class="iz-card-title">ÖNE ÇIKAN IZFIN SİNYALLERİ</div><table><thead><tr><th>VARLIK</th><th>FİYAT</th><th>IZFIN KARARI</th><th>SKOR</th><th>GÜVEN</th><th>MTF</th><th>RİSK</th></tr></thead><tbody>' + ''.join(rows) + '</tbody></table></div>'

def izfin_movers_html(max_n=6):
    sonuclar = st.session_state.get("sonuclar") or []
    paneller = st.session_state.get("teknik_paneller") or {}
    rows = []
    for r in sonuclar:
        t = str(r.get("Varlık", "")); p = paneller.get(t, {})
        try: deg = float(p.get("gunluk_degisim", 0) or 0)
        except Exception: deg = 0.0
        rows.append((abs(deg), deg, t, r.get("Fiyat", "—")))
    rows.sort(reverse=True)
    if not rows:
        body = '<div style="padding:22px 2px;color:#748ea2;font-size:11px">Akıllı Tarama sonrası listedeki dikkat çekici fiyat hareketleri burada görünecek.</div>'
    else:
        _parts = []
        for _, d, t, f in rows[:max_n]:
            _href = _iz_detail_href(t)
            _safe_t = html.escape(str(t))
            _parts.append(
                f'<a class="iz-mover-row iz-mover-link" href="{html.escape(_href, quote=True)}" title="{_safe_t} detay analizine git">'
                f'<div class="iz-mover-name">{_safe_t}<span class="iz-mini-arrow">↗</span></div>'
                f'<div class="iz-mover-price">{f}</div>'
                f'<div class="iz-mover-chg" style="color:{"#28e69d" if d>=0 else "#ff6673"}">{d:+.2f}%</div>'
                f'</a>'
            )
        body = ''.join(_parts)
    return f'<div class="iz-movers"><div class="iz-card-head"><div><div class="iz-card-title" style="margin:0">LİSTEDE DİKKAT ÇEKENLER</div><div class="iz-card-kicker">SON TARAMA EVRENİNDEKİ BELİRGİN HAREKETLER</div></div></div>{body}</div>'


def _izfin_home_ticker_ac(ticker):
    """Ana sayfadan aynı Streamlit oturumu içinde ilgili tarama detayını aç."""
    ticker = str(ticker or "").strip().upper()
    if not ticker:
        return
    paneller = st.session_state.get("teknik_paneller") or {}
    if ticker not in paneller:
        st.session_state["home_nav_mesaji"] = f"{ticker} için mevcut oturumda tarama detayı bulunamadı."
        return
    st.session_state["izfin_pending_detail_ticker"] = ticker
    st.session_state["izfin_scroll_to_detail"] = True
    st.session_state.izfin_nav = "🔎 Akıllı Tarama"


def _iz_score_bg(skor):
    skor = float(skor or 0)
    if skor >= 78: return "linear-gradient(145deg,#0b684e,#075743)"
    if skor >= 66: return "linear-gradient(145deg,#0b514a,#0a3f40)"
    if skor >= 55: return "linear-gradient(145deg,#123b45,#102f3b)"
    if skor >= 45: return "linear-gradient(145deg,#263842,#1e2d37)"
    return "linear-gradient(145deg,#5b202a,#421b23)"


def izfin_render_dashboard_native():
    """Piyasa nabzı + tıklanabilir fırsat haritası."""
    pulse,trend,momentum,flow,risk,kaynak = _iz_panel_metrics()
    trend_lbl = "GÜÇLÜ" if trend >= 70 else "İYİ" if trend >= 55 else "KARIŞIK"
    mom_lbl = "GÜÇLÜ" if momentum >= 70 else "İYİ" if momentum >= 55 else "KARIŞIK"
    flow_lbl = "POZİTİF" if flow >= 60 else "DENGELİ" if flow >= 45 else "ZAYIF"
    risk_lbl = "DÜŞÜK" if risk < 40 else "ORTA" if risk < 65 else "YÜKSEK"

    st.markdown(
        f"""
        <div class="iz-hero">
            <div class="iz-section-label">IZFIN SIGNATURE COMMAND CENTER</div>
            <h1>IZFIN Piyasa Merkezi</h1>
            <p>Piyasanın nabzını gör, fırsatı tara, kararın gerekçesini incele ve sonucu ölç.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    dash_left, dash_right = st.columns([1.15, .85], gap="large")

    with dash_left:
        st.markdown(
            f"""
            <div class="iz-card iz-native-pulse-card">
              <div class="iz-card-head">
                <div>
                    <div class="iz-card-title" style="margin:0">IZFIN PİYASA NABZI</div>
                    <div class="iz-card-kicker">{kaynak}</div>
                </div>
                <span class="iz-badge wait">{_iz_pulse_label(pulse)}</span>
              </div>
              <div class="iz-pulse">
                <div class="iz-gauge" style="--pulse:{pulse}%">
                    <div class="iz-gauge-content">
                        <div class="iz-gauge-num">{pulse}<span style="font-size:12px;color:#7890a3">/100</span></div>
                        <div class="iz-gauge-label">{_iz_pulse_label(pulse)}</div>
                    </div>
                </div>
                <div>
                    <div class="iz-pulse-copy">Trend, momentum, para akışı ve risk tek çerçevede okunur. Tarama sonrası nabız doğrudan IZFIN teknik motorunun analiz ettiği varlıklardan hesaplanır.</div>
                    <div class="iz-components">
                        <div class="iz-comp"><div class="iz-comp-name">TREND</div><div class="iz-comp-val">{trend}</div><div class="iz-comp-sub">{trend_lbl}</div></div>
                        <div class="iz-comp"><div class="iz-comp-name">MOMENTUM</div><div class="iz-comp-val">{momentum}</div><div class="iz-comp-sub">{mom_lbl}</div></div>
                        <div class="iz-comp"><div class="iz-comp-name">PARA AKIŞI</div><div class="iz-comp-val">{flow}</div><div class="iz-comp-sub">{flow_lbl}</div></div>
                        <div class="iz-comp"><div class="iz-comp-name">RİSK</div><div class="iz-comp-val">{risk}</div><div class="iz-comp-sub" style="color:#f2b94d">{risk_lbl}</div></div>
                    </div>
                </div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with dash_right:
        st.markdown(
            """
            <div class="iz-native-map-head">
                <div>
                    <div class="iz-card-title" style="margin:0">IZFIN FIRSAT HARİTASI</div>
                    <div class="iz-card-kicker">RENK = SKOR · ÇERÇEVE = GÜVEN</div>
                </div>
                <span>SIGNATURE MAP</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        _items = _iz_heatmap_items(max_n=12)
        if not _items:
            st.markdown(
                '<div class="iz-native-map-empty"><b>İlk Akıllı Tarama bekleniyor</b><span>Tarama sonrası hisseler burada görünecek.</span></div>',
                unsafe_allow_html=True,
            )
        else:
            # 3 kolon x en fazla 4 sıra; her kart gerçek Streamlit butonu.
            for row_start in range(0, len(_items), 3):
                _cols = st.columns(3, gap="small")
                for j, (s,g,t,d) in enumerate(_items[row_start:row_start+3]):
                    with _cols[j]:
                        _safe_key = re.sub(r"[^A-Za-z0-9_]+", "_", str(t))
                        _k = f"home_map_{_safe_key}_{row_start+j}"
                        _bg = _iz_score_bg(s)
                        _chg = f"{d:+.2f}%"
                        st.markdown(
                            f"""
                            <style>
                            .st-key-{_k} button{{
                                min-height:96px!important;
                                width:100%!important;
                                border-radius:13px!important;
                                background:{_bg}!important;
                                border:{max(1,int(g/28))}px solid rgba(38,238,220,.24)!important;
                                color:#f4fbff!important;
                                box-shadow:
                                    inset 0 1px 0 rgba(255,255,255,.05),
                                    0 10px 24px rgba(0,0,0,.18)!important;
                                white-space:pre-line!important;
                                font-size:11px!important;
                                line-height:1.45!important;
                                font-weight:760!important;
                                text-align:left!important;
                                justify-content:flex-start!important;
                                padding:13px 14px!important;
                                position:relative!important;
                            }}
                            .st-key-{_k} button:hover{{
                                transform:translateY(-3px)!important;
                                filter:brightness(1.1)!important;
                                border-color:#36d9e2!important;
                                box-shadow:
                                    inset 0 1px 0 rgba(255,255,255,.06),
                                    0 14px 28px rgba(0,0,0,.24),
                                    0 0 0 1px rgba(54,217,226,.12)!important;
                            }}
                            </style>
                            """,
                            unsafe_allow_html=True,
                        )
                        st.button(
                            f"{t}\nIZ {int(s)} · Güven {int(g)}%\n{_chg}\nDetayı aç",
                            key=_k,
                            use_container_width=True,
                            on_click=_izfin_home_ticker_ac,
                            args=(t,),
                        )


def izfin_render_top_signals_native(max_n=7):
    sonuclar = st.session_state.get("sonuclar") or []
    paneller = st.session_state.get("teknik_paneller") or {}
    sirali = sorted(
        sonuclar,
        key=lambda r: float(paneller.get(str(r.get("Varlık","")),{}).get("cezali_skor",0) or 0),
        reverse=True,
    )[:max_n]

    st.markdown(
        """
        <div class="iz-premium-section-head">
            <div>
                <small>IZFIN SIGNAL BOARD</small>
                <h3>Öne Çıkan IZFIN Sinyalleri</h3>
                <p>Son taramadaki en güçlü skor, güven ve MTF kombinasyonları</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not sirali:
        st.markdown('<div class="iz-native-empty">Akıllı Tarama çalıştırıldığında en yüksek skorlu sinyaller burada özetlenecek.</div>', unsafe_allow_html=True)
        return

    for idx, r in enumerate(sirali):
        t = str(r.get("Varlık","")); p = paneller.get(t,{})
        sin = str(r.get("Nihai Sinyal","—"))
        skor = int(float(p.get("cezali_skor",0) or 0))
        g = int(float(p.get("guven_skoru",50) or 50))
        fiyat = r.get("Fiyat","—")
        risk_v = p.get("risk_seviyesi",r.get("Risk","—"))
        mtf = int(float(p.get("mtf_uyum",50) or 50))
        _k = f"home_signal_{idx}_{re.sub(r'[^A-Za-z0-9_]+','_',t)}"

        card_left, card_mid, card_right = st.columns([1.45, 2.3, .9], gap="small")
        with card_left:
            st.button(
                f"{t}  ↗",
                key=_k,
                use_container_width=True,
                on_click=_izfin_home_ticker_ac,
                args=(t,),
            )
            st.markdown(f'<div class="iz-premium-price">{fiyat}</div>', unsafe_allow_html=True)

        with card_mid:
            st.markdown(
                f"""
                <div class="iz-premium-signal-body">
                    <div><span>KARAR</span><b class="iz-badge {_iz_badge_class(sin)}">{sin}</b></div>
                    <div><span>SKOR</span><strong>{skor}</strong></div>
                    <div><span>GÜVEN</span><strong>{g}%</strong></div>
                    <div><span>MTF</span><strong>{mtf}%</strong></div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with card_right:
            st.markdown(
                f"""
                <div class="iz-premium-risk">
                    <span>RİSK</span>
                    <b>{html.escape(str(risk_v))}</b>
                </div>
                """,
                unsafe_allow_html=True,
            )

def izfin_render_movers_native(max_n=6):
    sonuclar = st.session_state.get("sonuclar") or []
    paneller = st.session_state.get("teknik_paneller") or {}
    rows = []
    for r in sonuclar:
        t = str(r.get("Varlık","")); p = paneller.get(t,{})
        try: deg = float(p.get("gunluk_degisim",0) or 0)
        except Exception: deg = 0.0
        rows.append((abs(deg),deg,t,r.get("Fiyat","—")))
    rows.sort(reverse=True)

    st.markdown(
        """
        <div class="iz-premium-section-head">
            <div>
                <small>IZFIN MOVEMENT BOARD</small>
                <h3>Listede Dikkat Çekenler</h3>
                <p>Son tarama evrenindeki en belirgin günlük fiyat hareketleri</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if not rows:
        st.markdown('<div class="iz-native-empty">Akıllı Tarama sonrası listedeki dikkat çekici fiyat hareketleri burada görünecek.</div>', unsafe_allow_html=True)
        return

    for idx, (_,d,t,f) in enumerate(rows[:max_n]):
        k = f"home_mover_{idx}_{re.sub(r'[^A-Za-z0-9_]+','_',t)}"
        c1,c2,c3 = st.columns([1.55,.9,.8], gap="small")
        with c1:
            st.button(
                f"{t}  ↗",
                key=k,
                use_container_width=True,
                on_click=_izfin_home_ticker_ac,
                args=(t,),
            )
        with c2:
            st.markdown(
                f'<div class="iz-premium-mover-price">{f}</div>',
                unsafe_allow_html=True,
            )
        with c3:
            _cls = "up" if d >= 0 else "down"
            st.markdown(
                f'<div class="iz-premium-mover-change {_cls}">{d:+.2f}%</div>',
                unsafe_allow_html=True,
            )

def izfin_home_action_html():
    return '''<div class="iz-cta"><div class="iz-section-label">AKILLI TARAMA</div><h3>Fırsatı geniş havuzda keşfet</h3><p>Seçtiğin piyasa grubunu IZFIN karar motoruyla tara; skor, güven, giriş kalitesi, MTF ve risk filtrelerini aynı tabloda karşılaştır.</p></div>'''

def _google_state_uret():
    """OAuth state'i Streamlit session'a bağımlı olmadan imzalar (10 dk geçerli)."""
    if not GOOGLE_OAUTH_CLIENT_SECRET:
        return ""
    ts = str(int(time.time()))
    nonce = pysecrets.token_urlsafe(16)
    payload = f"{ts}.{nonce}"
    sig = hmac.new(
        GOOGLE_OAUTH_CLIENT_SECRET.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"{payload}.{sig}"


def _google_state_dogrula(state):
    try:
        ts, nonce, sig = str(state or "").split(".", 2)
        payload = f"{ts}.{nonce}"
        beklenen = hmac.new(
            GOOGLE_OAUTH_CLIENT_SECRET.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(sig, beklenen):
            return False
        yas = int(time.time()) - int(ts)
        return 0 <= yas <= 600
    except Exception:
        return False


def _google_oauth_url():
    if not GOOGLE_OAUTH_CLIENT_ID or not GOOGLE_OAUTH_CLIENT_SECRET:
        return ""
    params = {
        "client_id": GOOGLE_OAUTH_CLIENT_ID,
        "redirect_uri": GOOGLE_OAUTH_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "state": _google_state_uret(),
        "prompt": "select_account",
        "include_granted_scopes": "true",
    }
    return GOOGLE_OAUTH_AUTHORIZE_URL + "?" + urlencode(params)


def _google_tokenu_firebase_tokenina_cevir(google_id_token):
    if not FIREBASE_WEB_API_KEY:
        return None, "Firebase Web API Key eksik."
    try:
        post_body = urlencode({"id_token": google_id_token, "providerId": "google.com"})
        r = requests.post(
            f"{FIREBASE_AUTH_BASE}/accounts:signInWithIdp?key={FIREBASE_WEB_API_KEY}",
            json={
                "postBody": post_body,
                "requestUri": GOOGLE_OAUTH_REDIRECT_URI,
                "returnIdpCredential": True,
                "returnSecureToken": True,
            },
            timeout=12,
        )
        data = r.json() if r.content else {}
        if r.ok and data.get("idToken"):
            return data, None
        kod = ((data.get("error") or {}).get("message") or data.get("errorMessage") or f"HTTP_{r.status_code}")
        if "EMAIL_EXISTS" in str(kod):
            return None, "Bu Google e-postası mevcut başka bir IZFIN hesabıyla çakışıyor. Önce mevcut yöntemle giriş yapın."
        return None, f"Firebase Google oturumu oluşturulamadı: {kod}"
    except Exception as e:
        izfin_hata_logla("google_firebase_exchange", e)
        return None, "Google kimliği Firebase hesabına bağlanamadı."


def _google_callback_isle():
    try:
        oauth_error = str(st.query_params.get("error", "") or "").strip()
        code = str(st.query_params.get("code", "") or "").strip()
        state = str(st.query_params.get("state", "") or "").strip()
    except Exception:
        oauth_error = code = state = ""

    if oauth_error:
        try: st.query_params.clear()
        except Exception: pass
        if oauth_error == "access_denied":
            return False, "Google girişi kullanıcı tarafından iptal edildi."
        return False, f"Google OAuth hatası: {oauth_error}"
    if not code:
        return None
    if not GOOGLE_OAUTH_CLIENT_SECRET or not _google_state_dogrula(state):
        try: st.query_params.clear()
        except Exception: pass
        return False, "Google oturumu güvenlik doğrulamasından geçemedi. Lütfen yeniden deneyin."

    try:
        token_resp = requests.post(
            GOOGLE_OAUTH_TOKEN_URL,
            data={
                "code": code,
                "client_id": GOOGLE_OAUTH_CLIENT_ID,
                "client_secret": GOOGLE_OAUTH_CLIENT_SECRET,
                "redirect_uri": GOOGLE_OAUTH_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
            timeout=12,
        )
        token_data = token_resp.json() if token_resp.content else {}
        if not token_resp.ok:
            aciklama = token_data.get("error_description") or token_data.get("error") or f"HTTP_{token_resp.status_code}"
            try: st.query_params.clear()
            except Exception: pass
            return False, f"Google yetkilendirme kodu doğrulanamadı: {aciklama}"
        google_id_token = str(token_data.get("id_token") or "")
        if not google_id_token:
            try: st.query_params.clear()
            except Exception: pass
            return False, "Google kimlik tokenı alınamadı."

        firebase_data, err = _google_tokenu_firebase_tokenina_cevir(google_id_token)
        if err:
            try: st.query_params.clear()
            except Exception: pass
            return False, err
        ok, msg = _oturum_ac(firebase_data, beni_hatirla=True)
        try: st.query_params.clear()
        except Exception: pass
        return ok, msg
    except Exception as e:
        izfin_hata_logla("google_oauth_callback", e)
        try: st.query_params.clear()
        except Exception: pass
        return False, "Google oturumu tamamlanamadı. Lütfen tekrar deneyin."


def _google_login_component():
    """Google OAuth'u Streamlit'in native link bileşeniyle tarayıcıda başlatır."""
    if not GOOGLE_OAUTH_CLIENT_ID:
        st.info("Google ile giriş için GOOGLE_OAUTH_CLIENT_ID eksik.")
        return
    if not GOOGLE_OAUTH_CLIENT_SECRET:
        st.info("Google ile giriş için GOOGLE_OAUTH_CLIENT_SECRET Streamlit Secrets'a eklenmeli.")
        return

    auth_url = _google_oauth_url()
    if not auth_url:
        st.info("Google OAuth yapılandırması tamamlanamadı.")
        return

    st.link_button(
        "Google ile devam et",
        auth_url,
        key="google_oauth_native",
        type="secondary",
        use_container_width=True,
        help="Google hesabınızla güvenli şekilde devam edin.",
    )

def izfin_auth_ekrani():
    callback = _google_callback_isle()
    if callback:
        ok, msg = callback
        if ok:
            st.success("Google hesabınızla giriş yapıldı.")
            time.sleep(.15)
            st.rerun()
        elif msg:
            st.error(msg)

    _captcha_hazirla()
    if "izfin_auth_mode" not in st.session_state:
        st.session_state.izfin_auth_mode = "login"

    st.markdown('<div class="iz-auth-bg"></div>', unsafe_allow_html=True)
    st.markdown(f'''<div class="iz-auth-shell">
      <div class="iz-auth-logo">
        <img src="data:image/png;base64,{IZFIN_LOGO_B64}" alt="IZFIN">
        <div><div class="word">IZFIN</div><div class="tag">ANALYZE • PREDICT • INVEST</div></div>
      </div>
      <div class="iz-auth-kicker">SIGNATURE INTELLIGENCE</div>
      <div class="iz-auth-title">Hoş Geldiniz</div>
      <div class="iz-auth-sub">Piyasayı analiz et, fırsatları filtrele, kararını tek merkezden yönet.</div>
    </div>''', unsafe_allow_html=True)

    _, center, _ = st.columns([1.15, 1.55, 1.15])
    with center:
        st.markdown('<div class="iz-auth-card"><div class="iz-auth-card-head"><strong>IZFIN Hesabı</strong><span>GÜVENLİ OTURUM</span></div></div>', unsafe_allow_html=True)
        if not FIREBASE_WEB_API_KEY:
            st.error("Giriş sistemi yapılandırması eksik: Streamlit Secrets içine FIREBASE_WEB_API_KEY eklenmeli.")

        st.markdown('<div class="iz-auth-switch-label">HESAP ERİŞİMİ</div>', unsafe_allow_html=True)
        sw1, sw2 = st.columns(2, gap="small")
        with sw1:
            if st.button("Giriş Yap", key="auth_switch_login", type="primary" if st.session_state.izfin_auth_mode == "login" else "secondary", use_container_width=True):
                st.session_state.izfin_auth_mode = "login"
                st.rerun()
        with sw2:
            if st.button("Kayıt Ol", key="auth_switch_register", type="primary" if st.session_state.izfin_auth_mode == "register" else "secondary", use_container_width=True):
                st.session_state.izfin_auth_mode = "register"
                st.rerun()

        if st.session_state.izfin_auth_mode == "login":
            with st.form("izfin_login_form", clear_on_submit=False):
                email = st.text_input("E-posta", placeholder="ornek@email.com").strip().lower()
                password = st.text_input("Şifre", type="password", placeholder="Şifreniz")
                remember = st.checkbox("Beni hatırla", value=True)
                login_btn = st.form_submit_button("Giriş Yap", type="primary", use_container_width=True)
            if login_btn:
                if not email or not password:
                    st.error("E-posta ve şifre gerekli.")
                else:
                    data, err = _firebase_auth_post("signInWithPassword", {"email": email, "password": password, "returnSecureToken": True})
                    if err:
                        st.error(err)
                    else:
                        ok, msg = _oturum_ac(data, beni_hatirla=remember)
                        if ok:
                            st.success("Giriş başarılı.")
                            time.sleep(.2)
                            st.rerun()
                        else:
                            st.error(msg)
            with st.expander("Şifremi unuttum", expanded=False):
                reset_email = st.text_input("Şifre sıfırlama e-postası", key="reset_email").strip().lower()
            st.markdown('<div class="iz-google-wrap"><div class="iz-google-caption">veya</div></div>', unsafe_allow_html=True)
            _google_login_component()
            st.markdown('<div class="iz-google-note">Google hesabınız Firebase Authentication üzerinden doğrulanır.</div>', unsafe_allow_html=True)

        else:
            st.caption("Yeni hesabınız kişisel izleme listenizi ve performans geçmişinizi size özel saklar.")
            with st.form("izfin_register_form", clear_on_submit=False):
                reg_email = st.text_input("E-posta", key="reg_email", placeholder="ornek@email.com").strip().lower()
                reg_pass = st.text_input("Şifre", key="reg_pass", type="password", help="En az 8 karakter; büyük harf, küçük harf ve rakam içersin.")
                reg_pass2 = st.text_input("Şifre Tekrar", key="reg_pass2", type="password")
                st.caption(f"İnsan doğrulaması: {st.session_state.captcha_a} + {st.session_state.captcha_b} = ?")
                captcha = st.text_input("Doğrulama sonucu", key=f"captcha_{st.session_state.captcha_nonce}")
                terms = st.checkbox("Kullanım koşullarını ve gizlilik bilgilendirmesini okudum.", key="reg_terms")
                register_btn = st.form_submit_button("Hesabımı Oluştur", type="primary", use_container_width=True)
            if register_btn:
                errors = []
                if "@" not in reg_email or "." not in reg_email.split("@")[-1]: errors.append("Geçerli bir e-posta girin.")
                if reg_pass != reg_pass2: errors.append("Şifreler eşleşmiyor.")
                if len(reg_pass) < 8 or not re.search(r"[A-ZÇĞİÖŞÜ]", reg_pass) or not re.search(r"[a-zçğıöşü]", reg_pass) or not re.search(r"\d", reg_pass): errors.append("Şifre en az 8 karakter, büyük/küçük harf ve rakam içermeli.")
                try: captcha_ok = int(captcha.strip()) == int(st.session_state.captcha_a + st.session_state.captcha_b)
                except Exception: captcha_ok = False
                if not captcha_ok: errors.append("Doğrulama işlemi yanlış.")
                if not terms: errors.append("Kullanım koşulları onaylanmalı.")
                if errors:
                    for e in errors: st.error(e)
                    _captcha_yenile()
                else:
                    data, err = _kayit_ol(reg_email, reg_pass)
                    if err:
                        st.error(err); _captcha_yenile()
                    else:
                        st.success("Hesabınız oluşturuldu. Giriş Yap bölümünden oturum açabilirsiniz.")
                        st.session_state.izfin_auth_mode = "login"
                        _captcha_yenile()
            st.markdown('<div class="iz-google-wrap"><div class="iz-google-caption">şifre oluşturmadan devam et</div></div>', unsafe_allow_html=True)
            _google_login_component()

        st.markdown('<div class="iz-auth-security"><span>◈ <b>Firebase Auth</b></span><span>◈ <b>Kişisel veri alanı</b></span><span>◈ <b>14 gün güvenli oturum</b></span></div>', unsafe_allow_html=True)

    st.markdown('<div class="iz-auth-shell"><div class="iz-auth-footer">IZFIN · ANALYZE • PREDICT • INVEST &nbsp;·&nbsp; Yatırım karar destek platformu</div></div>', unsafe_allow_html=True)

def izfin_tarama_tablosu_html(df):
    if df is None or df.empty:
        return '<div class="iz-table-wrap"><div style="padding:22px;color:#7895a9">Gösterilecek tarama sonucu yok.</div></div>'
    ana_cols=["Varlık","Fiyat","Nihai Sinyal","Gelişmiş Skor","Güven","🎯 Giriş Kalitesi","MTF Uyum","Risk","Para Akışı","PEG / Değerleme","Seans Dışı"]
    cols=[c for c in ana_cols if c in df.columns]
    esc=lambda v: html.escape(str(v if v is not None else "—"))
    heads=''.join(f'<th>{esc(c)}</th>' for c in cols); body=[]
    for _,row in df.iterrows():
        tds=[]
        for c in cols:
            s=str(row.get(c,"—")); cls=''; rendered=esc(s)
            if c=="Varlık": cls='ticker'
            elif c=="Gelişmiş Skor": cls='score'
            elif c=="Nihai Sinyal": rendered=f'<span class="iz-badge {_iz_badge_class(s)}">{esc(s)}</span>'
            elif c=="Risk":
                u=s.upper(); cls='risk-high' if ('YÜKSEK' in u or 'PANİK' in u) else ('risk-low' if ('DÜŞÜK' in u or 'SAKİN' in u) else 'risk-mid')
            elif c in ["PEG / Değerleme","Seans Dışı","Para Akışı"]: cls='muted'
            tds.append(f'<td class="{cls}">{rendered}</td>')
        body.append('<tr>'+''.join(tds)+'</tr>')
    return f'<div class="iz-table-wrap"><table class="iz-table"><thead><tr>{heads}</tr></thead><tbody>{"".join(body)}</tbody></table></div>'

if not st.session_state.get("user_email") or not st.session_state.get("user_uid"):
    izfin_auth_ekrani()
    st.stop()

st.sidebar.markdown(izfin_brand_html(), unsafe_allow_html=True)
st.markdown(izfin_market_bar_html(izfin_piyasa_bandi_verisi()), unsafe_allow_html=True)

with st.expander("📘 Nasıl Kullanılır? — Tablo, skorlar, sinyaller ve risk yönetimi", expanded=False):
    st.markdown("""
<div style="background:linear-gradient(135deg,#17191f,#20242d);border:1px solid #343a46;border-radius:14px;padding:20px 22px;margin-bottom:16px;">
  <div style="font-size:20px;font-weight:700;color:#ffffff;margin-bottom:8px;">IZFIN kullanım rehberi</div>
  <div style="color:#c8ced8;line-height:1.7;font-size:14px;">Bu ekran tek bir göstergeden “al” veya “sat” üretmez. Trend, momentum, hacim, para akışı, volatilite, likidite ve çoklu zaman dilimi verilerini birlikte değerlendirir. En sağlıklı kullanım; önce tabloyla adayları daraltmak, sonra detay paneliyle gerekçeyi okumak ve son olarak destek–stop–hedef planını kontrol etmektir.</div>
</div>
""", unsafe_allow_html=True)

    st.markdown("### 1) Önerilen kullanım sırası")
    st.markdown("""
1. **Varlıkları seçin ve Derin Taramayı çalıştırın.** İlk tarama; trendi, skoru, para akışını ve sinyali aynı tabloda karşılaştırır.  
2. **Sadece sinyal adına bakmayın.** Gelişmiş skor, risk seviyesi, MTF uyumu, veri kaynağı ve çok zaman dilimli giriş kalitesini birlikte okuyun.  
3. **Detay panelinde göstergelerin birbiriyle uyumunu kontrol edin.** RSI düşükken MACD ve para akışı hâlâ zayıfsa dönüş teyidi tamamlanmamış olabilir.  
4. **Destek, stop ve hedefleri işlemden önce birlikte okuyun.** Teknik seviyeler olasılık bölgesidir; tek bir hedef veya stop değeri kesin sonuç olarak görülmemelidir.  
5. **Sinyal performansı ve backtest sonuçlarını izleyin.** Stratejinin hangi piyasa ve RSI bölgelerinde daha iyi çalıştığını zaman içinde ölçün.
""")

    st.markdown("### 2) Tarama tablosundaki sütunlar nasıl okunur?")
    st.markdown("""
| Alan | Ne anlatır? | Nasıl yorumlanmalı? |
|---|---|---|
| **Varlık / Fiyat** | Güncel sembol, fiyat ve günlük değişim | Fiyatın tek başına ucuz veya pahalı olduğunu göstermez. |
| **Görec. Güç (Sektör)** | Yaklaşık 1 aylık performansın referans endekse göre farkı ve hacim oranı | Pozitif fark göreceli gücü; yüksek hacim oranı daha geniş katılımı gösterir. |
| **Hibrit / Cezalı Skor** | Eski cezalı skor ile yeni teyit bonus ve cezalarının birleşimi | **70+ güçlü**, **50–69 nötr/karışık**, **50 altı cezalı** bölgedir; başarı olasılığı değildir. |
| **Para Akışı** | MFI, OBV, CMF ve hacim davranışının özeti | Fiyat yükselirken para akışı zayıfsa hareketin kalıcılığı sorgulanmalıdır. |
| **PEG / Değerleme** | Şirketin büyümesine göre değerleme oranını ve kısa etiketi gösterir | Teknik skora dahil edilmez. Düşük pozitif PEG büyümeye göre daha makul değerlemeye, yüksek PEG daha yüksek büyüme primine işaret edebilir. |
| **Nihai Sinyal** | Algoritmanın teknik koşullara verdiği sınıflandırma | Emir değildir; sinyal açıklaması ve risk planıyla birlikte kullanılmalıdır. |
| **Giriş Kalitesi** | Normal seanstaki 5 dk, 15 dk ve 1 saat zamanlamasının alım ön sinyalini destekleyip desteklemediği | Premarket/after-hours mumları puana girmez. 85+ ve üst zaman dilimi teyidi varsa “Teyit Edildi”; 75+ güçlü, 55+ erken, 35+ hazırlanıyor, altı uygun değil olarak sınıflanır. |
| **Karma Destek / Direnç** | Tepe-dip, EMA50, Bollinger ve ATR’den türetilen karar seviyeleri | Destek altı kalıcılık riski; direnç üstü hacimli kapanış yükseliş senaryosunu güçlendirir. |
| **Süren Stop** | ATR/Chandelier mantığıyla hesaplanan teknik iptal noktası | Gap ve sert haber hareketlerinde fiyat stop seviyesini atlayabilir. |
| **TP1 / TP2 / TP3** | Giriş–stop riskinin gerçek teknik direnç ve volatilite seviyeleri | Fiyat tahmini değil, risk/ödül planlama seviyeleridir. |
| **Seans Dışı** | ABD hisselerinde varsa premarket/after-hours son fiyatı | Yalnızca ek bilgidir; skora, RSI/MACD/ATR’ye ve Giriş Kalitesine dahil edilmez. |
| **Veri Kaynağı** | Finnhub, Yahoo 5 dk veya fallback bilgisi | Teknik motor normal seans verisini kullanır; kaynaklar arasında küçük fiyat ve zaman farkları oluşabilir. |
""")

    st.markdown("### 3) Hibrit skor nasıl oluşur?")
    st.markdown("""
Skorun ana gövdesi **eski cezalı skor sistemidir**. Yeni göstergeler bu sistemi değiştirmek yerine kontrollü bonus veya ceza ekler.

**Eski skorun ana kalemleri**
- Fiyatın **SMA 200** üzerindeki konumu
- Fiyatın **EMA 50** üzerindeki konumu
- Hacim ve OBV uyumu
- RSI bölgesi
- MACD–sinyal çizgisi ilişkisi
- Bollinger konumu
- Likidite / sığ tahta cezası

**Gelişmiş doğrulama katmanı**
- ADX ve +DI/−DI ile trend gücü
- CMF ve diğer para akışı teyitleri
- SuperTrend yönü
- Seans VWAP konumu
- Sektöre/endekse göre göreceli güç
- 5 dk, 15 dk, 1 saat, 4 saat ve günlük zaman dilimi uyumu

Gelişmiş bonus ve cezalar sınırlandırılır; böylece yeni katman eski skorun karakterini bastırmaz. Detay panelindeki **“Skor nasıl oluştu?”** alanı puanları ayrı gösterir.
""")

    st.markdown("### 4) Sinyallerin doğru anlamı")
    st.markdown("""
- **🟢 Kusursuz Alım:** Uzun vadeli trend korunurken fiyatın Bollinger alt bandı/destek bölgesine güçlü biçimde geri çekildiği yüksek öncelikli adaydır. Düşük RSI dönüş garantisi değildir; hacim ve kısa vadeli tepki teyidi aranmalıdır.
- **🔵 Kademeli Alım:** Ana trend pozitif kalmasına rağmen kısa vadeli zayıflık sürmektedir. Kesin dönüş teyidi olmadığı için tek seferde tam pozisyon yerine kontrollü kademeler önerir.
- **🚀 Yükseliş Kırılımı:** Önceki direnç; hacim, EMA 9–21 ve trend desteğiyle aşılmıştır. Kırılan seviyenin destek olarak korunması kritiktir.
- **🌟 Uzun Vadeli Teknik Aday:** SMA 200 üzerindeki güçlü teknik trend ve yüksek skor yapısını gösterir. **Temel analiz veya GARP sinyali değildir.**
- **🟡 Hacimli Tepki:** Olağan dışı hacimli toparlanmadır; izleme sinyalidir, doğrudan alım sinyali değildir.
- **🟡 Momentum Aşırı Isındı:** Trend güçlüdür ancak fiyat kısa vadede üst bant/yüksek RSI bölgesindedir. Yeni alım yerine geri çekilme veya kırılan seviyenin destek olarak çalışması beklenir.
- **🟠 Kâr Realizasyonu:** Yüksek RSI ile birlikte MACD, kısa EMA veya para akışında bozulma oluştuğunda risk azaltma ve kısmi kâr koruma uyarısıdır.
- **🧗 Kurtuluş Çabası:** Ana trend zayıfken kısa vadeli toparlanmadır. SMA 200 ve güçlü hacim teyidi gelmeden dönüş tamamlanmış sayılmaz.
- **🔴 Uzak Dur:** Trend, momentum, para akışı veya likidite yapısında yeni alımı desteklemeyen ağır riskler vardır.
- **⚪ Nötr:** Sistem ortak yön bulamamıştır; işlem üretmek yerine teyit bekler.
""")

    st.markdown("### 5) Göstergeler birlikte nasıl okunur?")
    st.markdown("""
- **RSI:** 30 altı aşırı satış, 70 üstü aşırı alım için klasik referanstır; tek başına dönüş sinyali değildir.
- **MACD:** MACD'nin sinyal çizgisinin üzerinde olması momentum avantajını destekler; histogram yönü de önemlidir.
- **ADX / DI:** ADX trend gücünü ölçer. +DI > −DI yükseliş, −DI > +DI düşüş yönünü destekler.
- **MFI / OBV / CMF:** Fiyat hareketine para ve hacim katılımını ölçer. Ayrışma varsa sinyal güveni düşer.
- **VWAP:** Gün içi ortalama işlem maliyetidir. Fiyatın üzerinde kalması kısa vadeli alıcı avantajını destekleyebilir.
- **ATR:** Yön değil, hareket genişliği ve risk ölçüsüdür. ATR yükseldikçe teknik stop ve hedef aralıkları genişleyebilir.
- **MTF uyumu:** Zaman dilimlerinin aynı yönde olması teyidi artırır; çatışma varsa daha küçük pozisyon veya bekleme uygundur.
""")

    st.markdown("### 6) Destek, stop ve teknik hedefler")
    st.markdown("""
- **Karma destek/direnç**, geçmiş tepe-dip, EMA50, Bollinger ve ATR bileşimidir.
- **Süren stop**, ATR/Chandelier ve geçerli teknik destek yapısına göre dinamik biçimde güncellenir.
- **TP1 / TP2 / TP3**, önceki 20/50/100 günlük tepeler, Bollinger üst bant, ATR uzantıları, swing seviyeleri ve tarihsel volatilite projeksiyonunun kümelenmesinden üretilen teknik hedeflerdir.
- Yeni taramalarda güncel stop ve hedefler değişebilir. **Sinyal Performans Takibi** ise ilk alım anındaki stop ve TP1/TP2/TP3 değerlerini ayrıca dondurur ve geçmiş başarısını bu ilk plana göre ölçer.
- Aynı yönde yüksek korelasyonlu hisseler toplam portföy riskini büyütebilir.
""")

    st.markdown("### 7) Uygulama yapısı")
    st.markdown("""
- **🚀 Analiz Merkezi:** Derin tarama, detaylı teknik analiz, şeffaf karar motoru ve isteğe bağlı projeksiyon/senaryo analizi tek akışta sunulur.
- **📊 Takip & Performans:** Gerçekte oluşmuş alım dönemlerini, aktif/kapanmış pozisyonları ve 1/5/10/20/45 günlük performans karnesini birlikte izler.
- **🧪 Strateji Laboratuvarı:** IZFIN Daily Core motorunu geçmiş veride yeniden çalıştırır; özet başarı ölçümleri ve geçmiş karar ayrıntıları aynı bölümde tutulur.
- **Hesap güvenliği:** Email/Password girişi Firebase Authentication ile doğrulanır; “Beni hatırla” seçeneğinde Firebase session cookie kullanılır. Kişisel liste ve takip verileri kullanıcı UID'sine bağlı tutulur.
""")

    st.warning("Bu uygulama algoritmik teknik analiz ve karar desteği sağlar; yatırım tavsiyesi, kesin getiri veya zarar etmeme garantisi değildir. Haber, bilanço, makro gelişme, likidite ve piyasa boşlukları teknik seviyeleri geçersiz kılabilir.")

if "izfin_nav" not in st.session_state:
    st.session_state.izfin_nav = "🏠 Ana Sayfa"

def _izfin_nav_to(hedef):
    st.session_state.izfin_nav = hedef

st.sidebar.markdown('<div class="iz-nav-label" style="margin-top:14px">NAVİGASYON</div>', unsafe_allow_html=True)
for _nav_label in ["🏠 Ana Sayfa", "🔎 Akıllı Tarama", "🎯 Projeksiyon & Senaryo", "📊 Takip & Performans", "🧪 Strateji Laboratuvarı"]:
    st.sidebar.button(
        _nav_label,
        key=f"nav_{_nav_label}",
        type="primary" if st.session_state.izfin_nav == _nav_label else "secondary",
        use_container_width=True,
        on_click=_izfin_nav_to,
        args=(_nav_label,),
    )
aktif_sayfa = st.session_state.izfin_nav

st.sidebar.markdown("---")
st.sidebar.markdown('<div class="iz-nav-label">KONTROL MERKEZİ</div>', unsafe_allow_html=True)
st.sidebar.markdown(f'<div class="iz-account-chip"><b>{html.escape(st.session_state.user_email)}</b><span>Kişisel IZFIN hesabı · listeleriniz ve takip verileriniz size özeldir</span></div>', unsafe_allow_html=True)
st.sidebar.caption(f"Çalışan sürüm: {IZFIN_APP_SURUMU}")
if not FINNHUB_API_KEY:
    st.sidebar.caption("ℹ️ Finnhub yok: ABD quote katmanı Yahoo fallback ile devam ediyor.")

# v1.7.14 — Sidebar yalnızca navigasyon ve hesap alanıdır.
selected_tickers = list(st.session_state.get("secilen_varliklar", []))
tarama_tetiklendi = False

st.sidebar.markdown("---")
if st.sidebar.button("🚪 Çıkış Yap", use_container_width=True):
    try:
        cookie_manager.delete("izfin_session"); cookie_manager.delete("user_email")
    except Exception: pass
    st.session_state.user_email=None; st.session_state.user_uid=None
    st.session_state.custom_tickers=VARSAYILAN_TICKERS.copy(); st.session_state.secilen_varliklar=VARSAYILAN_TICKERS.copy()
    st.session_state.kullanici_listesi_yuklendi=False; st.session_state.logout_triggered=True
    time.sleep(.2); st.rerun()

if aktif_sayfa in ["🏠 Ana Sayfa", "🔎 Akıllı Tarama"]:
    if aktif_sayfa == "🏠 Ana Sayfa":
        _home_msg = st.session_state.pop("home_nav_mesaji", None)
        if _home_msg:
            st.warning(_home_msg)

        izfin_render_dashboard_native()

        st.markdown('<div class="iz-home-scan-banner"><div class="copy"><strong>✦ Fırsatları tüm evrende tara</strong><span>IZFIN merkezi karar motorunu seçtiğiniz piyasa grubunda çalıştırın.</span></div><span class="iz-badge wait">SIGNATURE SCAN</span></div>', unsafe_allow_html=True)
        if st.button("✦ AKILLI TARAMA MERKEZİNE GİT →", type="primary", use_container_width=True, key="home_scan_primary"):
            _izfin_nav_to("🔎 Akıllı Tarama"); st.rerun()

        izfin_render_top_signals_native()

        hc1, hc2 = st.columns([1.45, .85], gap="large")
        with hc1:
            izfin_render_movers_native()
        with hc2:
            st.markdown(izfin_home_action_html(), unsafe_allow_html=True)
    else:
        st.markdown('''<div class="iz-scanner-hero"><div><div class="iz-section-label">IZFIN SCANNER</div><h2>Akıllı Tarama Merkezi</h2><p>Varlık evrenini seç, merkezi karar motorunu çalıştır ve sonuçları skor · güven · giriş kalitesi · MTF · risk ekseninde karşılaştır.</p></div><span class="iz-badge wait">SIGNATURE SCAN</span></div>''', unsafe_allow_html=True)

        # --- v1.7.14: Akıllı Tarama ana çalışma alanı ---
        if st.session_state.pop("liste_kurtarma_mesaji", False):
            st.success("Eski kişisel listeniz Firebase hesabınıza geri bağlandı.")

        st.markdown(
            f"""
            <div class="iz-scan-control-head">
              <div>
                <div class="iz-section-label">TARAMA KONTROL PANELİ</div>
                <h3>Evreni hazırla ve taramayı başlat</h3>
                <p>Hisse ekleme, kişisel liste, profil ve tarama seçimi artık tek çalışma alanında.</p>
              </div>
              <div class="iz-scan-count">KİŞİSEL LİSTE · {len(st.session_state.get("custom_tickers", []))} VARLIK</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        scan_left, scan_right = st.columns([1.0, 1.15], gap="large")

        with scan_left:
            st.markdown("""<div class="iz-panel-title"><span class="iz-panel-icon">⌕</span><div><b>Hisse Ara & Listem</b><small>Piyasalarda ara, kişisel evrenini oluştur</small></div></div>""", unsafe_allow_html=True)
            search_col, search_btn_col = st.columns([5.2, 1.0], gap="small")
            with search_col:
                _arama = st.text_input(
                    "Hisse / şirket ara",
                    key="ek_hisse_arama",
                    placeholder="Örn. APP, Apple, NVDA, THYAO...",
                    help="Sembolün veya şirket adının ilk harflerini yazın. Enter'a basabilir veya Ara butonunu kullanabilirsiniz.",
                )
            with search_btn_col:
                st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
                _ara_tiklandi = st.button(
                    "Ara",
                    key="stock_search_button",
                    use_container_width=True,
                    type="secondary",
                )

            # Yazı değiştiğinde Streamlit zaten rerun eder; Ara butonu da aynı akışı tetikler.
            # Böylece hem Enter hem tıklama kullanılabilir.
            _arama_aktif = bool(_arama.strip()) and (
                _ara_tiklandi
                or st.session_state.get("_son_hisse_arama") != _arama.strip()
                or st.session_state.get("_son_hisse_arama") == _arama.strip()
            )

            if _arama_aktif:
                st.session_state["_son_hisse_arama"] = _arama.strip()
                with st.spinner("Piyasalarda aranıyor..."):
                    _oneriler = hisse_onerileri_getir(_arama)
            else:
                _oneriler = []

            if _oneriler:
                st.caption(f"🔎 {len(_oneriler)} eşleşme bulundu")
                _labels = []
                for x in _oneriler:
                    _name = x.get("name") or "Şirket adı yok"
                    _exchange = x.get("exchange") or ""
                    _labels.append(
                        f"{x['symbol']}  —  {_name[:48]}"
                        + (f"  ·  {_exchange}" if _exchange else "")
                    )

                _idx = st.selectbox(
                    "Arama sonuçları",
                    options=list(range(len(_oneriler))),
                    format_func=lambda i: _labels[i],
                    key="hisse_oneri_secimi",
                    help="Eklemek istediğiniz hisseyi seçin.",
                )

                _chosen = _oneriler[int(_idx)]
                st.markdown(
                    f"""<div class="iz-search-result-preview">
                    <div><b>{_chosen['symbol']}</b><span>{_chosen.get('name') or 'Şirket adı yok'}</span></div>
                    <small>{_chosen.get('exchange') or 'Piyasa bilgisi yok'}</small>
                    </div>""",
                    unsafe_allow_html=True,
                )

                if st.button(
                    f"＋ {_chosen['symbol']} Listeme Ekle",
                    use_container_width=True,
                    key="autocomplete_add",
                    type="primary",
                ):
                    _symbol = str(_chosen["symbol"]).strip().upper()
                    if _symbol in st.session_state.custom_tickers:
                        st.session_state["liste_islem_mesaji"] = (
                            "warning",
                            f"{_symbol} zaten kişisel listenizde bulunuyor."
                        )
                    else:
                        _eski_liste = st.session_state.custom_tickers.copy()
                        try:
                            st.session_state.custom_tickers.append(_symbol)
                            kullanici_listesini_kaydet()
                            st.session_state.aktif_profil = "Kendi Listem"
                            st.session_state.secilen_varliklar = st.session_state.custom_tickers.copy()
                            st.session_state["liste_islem_mesaji"] = (
                                "success",
                                f"{_symbol} kişisel listenize başarıyla eklendi."
                            )
                        except Exception as _ekleme_hatasi:
                            st.session_state.custom_tickers = _eski_liste
                            st.session_state["liste_islem_mesaji"] = (
                                "error",
                                f"{_symbol} listeye eklenemedi: Firebase kaydı tamamlanamadı. {_ekleme_hatasi}"
                            )
                    st.rerun()
            elif _arama.strip():
                st.warning("Bu aramayla eşleşen piyasa sembolü bulunamadı.")

            with st.expander("Kişisel Listemi Yönet", expanded=True):
                _liste_mesaji = st.session_state.pop("liste_islem_mesaji", None)
                if _liste_mesaji:
                    _tip, _metin = _liste_mesaji
                    if _tip == "success":
                        st.success(_metin)
                    elif _tip == "warning":
                        st.warning(_metin)
                    else:
                        st.error(_metin)

                if st.session_state.custom_tickers:
                    st.caption(f"{len(st.session_state.custom_tickers)} kayıtlı varlık")
                    _kayitli_html = "".join(
                        f'<span class="iz-static-chip">{x}</span>'
                        for x in st.session_state.custom_tickers
                    )
                    st.markdown(
                        f"""
                        <div class="iz-saved-list-label">Kayıtlı hisselerim</div>
                        <div class="iz-static-chip-wrap iz-saved-list-box">{_kayitli_html}</div>
                        """,
                        unsafe_allow_html=True,
                    )
                else:
                    st.caption("Henüz kişisel listenizde varlık yok.")

                m1, m2 = st.columns(2)
                with m1:
                    st.text_input("Sembol ekle", key="ek_hisse_input_field", placeholder="örn. RKLB")
                    st.button(
                        "＋ Manuel Ekle",
                        on_click=hisse_ekle_callback,
                        use_container_width=True,
                        key="main_manual_add",
                    )
                with m2:
                    st.text_input("Sembol sil", key="sil_hisse_input_field", placeholder="örn. AAPL")
                    st.button(
                        "− Kalıcı Sil",
                        on_click=hisse_sil_callback,
                        use_container_width=True,
                        key="main_manual_delete",
                    )

        with scan_right:
            st.markdown("""<div class="iz-panel-title"><span class="iz-panel-icon">◎</span><div><b>Tarama Evreni</b><small>Profilini ve taranacak varlıkları belirle</small></div></div>""", unsafe_allow_html=True)
            st.selectbox(
                "Profil",
                list(preset_options.keys()),
                index=list(preset_options.keys()).index(st.session_state.aktif_profil),
                key="profil_selectbox_key",
                on_change=profil_degisti,
                help="Hazır piyasa profili seçebilir veya Kendi Listem ile kişisel listenizi tarayabilirsiniz.",
            )

            # v1.7.19 — Ayrı "Taranacak Varlıklar" seçicisi kaldırıldı.
            # Profil Kendi Listem ise kullanıcının Firebase'deki kişisel listesi doğrudan taranır.
            # Diğer hazır profiller seçilirse ilgili preset doğrudan kullanılır.
            if st.session_state.aktif_profil == "Kendi Listem":
                selected_tickers = list(dict.fromkeys([
                    str(x).strip().upper()
                    for x in st.session_state.custom_tickers
                    if str(x).strip()
                ]))
                st.session_state.secilen_varliklar = selected_tickers.copy()

                _liste_html = "".join(
                    f'<span class="iz-static-chip">{x}</span>'
                    for x in selected_tickers
                ) or '<span class="iz-empty-list">Listenizde henüz hisse yok</span>'

                st.markdown(
                    f"""
                    <div class="iz-active-universe">
                        <div class="iz-active-universe-top">
                            <div>
                                <small>AKTİF TARAMA EVRENİ</small>
                                <strong>Kendi Listem</strong>
                            </div>
                            <span>{len(selected_tickers)} VARLIK</span>
                        </div>
                        <div class="iz-static-chip-wrap">{_liste_html}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            else:
                selected_tickers = list(dict.fromkeys([
                    str(x).strip().upper()
                    for x in preset_options.get(st.session_state.aktif_profil, [])
                    if str(x).strip()
                ]))
                st.session_state.secilen_varliklar = selected_tickers.copy()

                st.markdown(
                    f"""
                    <div class="iz-active-universe">
                        <div class="iz-active-universe-top">
                            <div>
                                <small>AKTİF TARAMA EVRENİ</small>
                                <strong>{st.session_state.aktif_profil}</strong>
                            </div>
                            <span>{len(selected_tickers)} VARLIK</span>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            st.markdown(
                f"""<div class="iz-scan-selection-summary"><b>{len(selected_tickers)}</b><span> varlık taramaya hazır</span></div>""",
                unsafe_allow_html=True,
            )

            tarama_tetiklendi = st.button(
                "AKILLI TARAMAYI BAŞLAT",
                type="primary",
                use_container_width=True,
                key="main_signature_scan",
            )
            st.caption("Tarama; IZFIN skor, güven, giriş kalitesi, MTF, risk ve para akışı katmanlarını birlikte çalıştırır.")
    if tarama_tetiklendi:
        if not selected_tickers:
            st.warning("⚠️ Taramayı başlatmadan önce yukarıdaki Tarama Evreni bölümünden en az bir varlık seçin.")
        else:
            with st.spinner("Piyasa geçmişi ve güncel seans canlı fiyatları çekiliyor..."):
                st.session_state.opsiyon_sonuclar = None
                st.session_state.taramada_hatalar = []
                
                # Günlük ve gün içi veriler toplu indirilir; her hisse için ayrı Yahoo
                # isteği açılmadığı için büyük listelerde tarama belirgin biçimde hızlanır.
                toplu_df = taze_veri_indir(tuple(selected_tickers))
                toplu_intraday = toplu_intraday_veri_cek(tuple(selected_tickers), interval="5m", period="5d")
                quote_haritasi = finnhub_quotelari_paralel_cek(list(selected_tickers))
                # PEG, teknik skordan tamamen bağımsız bir temel değerleme katmanıdır.
                # 6 saat önbelleğe alınır ve hisseler paralel sorgulanır.
                peg_haritasi = peg_verilerini_paralel_cek(list(selected_tickers))
                
                gecici_sonuclar = []
                gecici_sozlu_analizler = {}
                gecici_teknik_paneller = {}
                basarisi_cekilemeyen_varliklar = []
                boga_sayisi = alim_firsati = 0
                
                sektor_referanslari = {"XU100.IS": "BIST100", "^IXIC": "NASDAQ", "XBANK.IS": "Banka", "XUSIN.IS": "Sanayi"}
                sektor_getirileri = {}
                
                try:
                    sektor_toplu = yf.download(
                        list(sektor_referanslari.keys()), period="40d", group_by="ticker",
                        progress=False, threads=True, auto_adjust=True, timeout=8
                    )
                except Exception as e:
                    izfin_hata_logla("yahoo_sektor_toplu", e)
                    sektor_toplu = pd.DataFrame()
                for sembol in sektor_referanslari.keys():
                    try:
                        df_sek = toplu_veriden_ticker_ayir(sektor_toplu, sembol, len(sektor_referanslari))
                        if 'Close' in df_sek:
                            sek_close = pd.to_numeric(df_sek['Close'], errors='coerce').replace([np.inf, -np.inf], np.nan).dropna()
                            if len(sek_close) >= 21 and float(sek_close.iloc[-21]) != 0:
                                sektor_getirileri[sembol] = ((float(sek_close.iloc[-1]) - float(sek_close.iloc[-21])) / float(sek_close.iloc[-21])) * 100
                            else:
                                sektor_getirileri[sembol] = np.nan
                        else:
                            sektor_getirileri[sembol] = np.nan
                    except Exception:
                        sektor_getirileri[sembol] = np.nan

                ilerleme = st.progress(0, text="Tarama hazırlanıyor...")
                toplam_ticker = max(len(selected_tickers), 1)
                for sira, ticker in enumerate(selected_tickers, start=1):
                    ilerleme.progress((sira - 1) / toplam_ticker, text=f"{ticker} analiz ediliyor ({sira}/{toplam_ticker})")
                    try:
                        df_long = gunluk_toplu_veriden_ticker_ayir(
                            toplu_df, ticker, len(selected_tickers)
                        )
                        
                        if isinstance(df_long.columns, pd.MultiIndex): 
                            df_long.columns = df_long.columns.get_level_values(0)
                            
                        df_long = df_long.dropna(subset=['Close', 'Volume'])
                        
                        if df_long.empty or len(df_long) < 30:
                            basarisi_cekilemeyen_varliklar.append(ticker)
                            continue
                        
                        is_bist = ".IS" in ticker
                        para_birimi = "TL" if is_bist else "$"
                        
                        # --- CANLI OHLCV: FINNHUB + YAHOO 5 DAKİKALIK FALLBACK ---
                        intraday_ticker = toplu_veriden_ticker_ayir(toplu_intraday, ticker, len(selected_tickers))
                        df_long, df_intraday, veri_kaynagi, ham_intraday = canli_ohlcv_ile_guncelle(
                            ticker, df_long, intraday_hazir=intraday_ticker, quote_hazir=quote_haritasi.get(ticker)
                        )
                        seans_disi_metin, seans_disi_fiyat = seans_disi_ozet(ticker, ham_intraday, quote_haritasi.get(ticker))
                        bugun_kapanis = float(df_long['Close'].iloc[-1])

                        onceki_kapanis = float(df_long['Close'].iloc[-2]) if len(df_long) >= 2 else bugun_kapanis
                        gunluk_degisim = ((bugun_kapanis - onceki_kapanis) / onceki_kapanis) * 100 if onceki_kapanis > 0 else 0.0
                        fiyat_str = f"{bugun_kapanis:.2f} {para_birimi} ({'+' if gunluk_degisim > 0 else ''}{gunluk_degisim:.2f}%)"

                        ortalama_hacim_20 = df_long['Volume'].rolling(20).mean().iloc[-1]
                        ortalama_ciro_tutar = ortalama_hacim_20 * bugun_kapanis if not pd.isna(ortalama_hacim_20) else 0
                        is_sig_tahta = ortalama_ciro_tutar < (50_000_000 if is_bist else 5_000_000)

                        # Göreceli güç hesabında yalnızca geçerli kapanışları kullan.
                        # Yahoo bazı sembollerde ilk/son satırı NaN döndürebildiği için
                        # ham iloc kullanmak `%nan` üretebiliyordu.
                        close_1m = pd.to_numeric(df_long['Close'], errors='coerce').replace([np.inf, -np.inf], np.nan).dropna().tail(21)
                        hisse_1m_getiri = np.nan
                        if len(close_1m) >= 2 and float(close_1m.iloc[0]) != 0:
                            hisse_1m_getiri = ((float(close_1m.iloc[-1]) - float(close_1m.iloc[0])) / float(close_1m.iloc[0])) * 100

                        sek_sembol = "XU100.IS" if is_bist else "^IXIC"
                        sektor_get = sektor_getirileri.get(sek_sembol, np.nan)
                        sektor_get = float(sektor_get) if pd.notna(sektor_get) and np.isfinite(float(sektor_get)) else np.nan
                        sektorel_fark = (hisse_1m_getiri - sektor_get) if np.isfinite(hisse_1m_getiri) and np.isfinite(sektor_get) else np.nan

                        bugun_hacim = pd.to_numeric(pd.Series([df_long['Volume'].iloc[-1]]), errors='coerce').iloc[0]
                        hacim_sma20 = pd.to_numeric(df_long['Volume'], errors='coerce').replace([np.inf, -np.inf], np.nan).rolling(20, min_periods=5).mean().iloc[-1]
                        hacim_oran = (float(bugun_hacim) / float(hacim_sma20)) * 100 if pd.notna(bugun_hacim) and pd.notna(hacim_sma20) and float(hacim_sma20) > 0 else 100.0
                        if pd.notna(sektorel_fark) and np.isfinite(float(sektorel_fark)):
                            gorec_guc_str = f"{'+' if sektorel_fark > 0 else ''}{sektorel_fark:.1f}% | Vol: %{hacim_oran:.0f}"
                        else:
                            gorec_guc_str = f"— Veri yok | Vol: %{hacim_oran:.0f}"

                        delta = df_long['Close'].diff()
                        rs = delta.where(delta>0, 0.0).ewm(alpha=1/14, adjust=False).mean() / (-delta.where(delta<0, 0.0).ewm(alpha=1/14, adjust=False).mean() + 1e-5)
                        rsi = 100 - (100 / (1 + rs)).iloc[-1]
                        
                        macd_serisi = df_long['Close'].ewm(span=12, adjust=False).mean() - df_long['Close'].ewm(span=26, adjust=False).mean()
                        macd_sinyal = macd_serisi.ewm(span=9, adjust=False).mean()
                        
                        sma_200 = df_long['Close'].rolling(200).mean().iloc[-1] if len(df_long) >= 200 else df_long['Close'].mean()
                        uzun_vade_trend = bugun_kapanis > sma_200

                        bb_mid = df_long['Close'].rolling(20).mean().iloc[-1]
                        bb_ust = (df_long['Close'].rolling(20).mean() + (df_long['Close'].rolling(20).std() * 2)).iloc[-1]
                        bb_alt = (df_long['Close'].rolling(20).mean() - (df_long['Close'].rolling(20).std() * 2)).iloc[-1]

                        typical_price = (df_long['High'] + df_long['Low'] + df_long['Close']) / 3
                        raw_money_flow = typical_price * df_long['Volume']
                        pos_flow = pd.Series(np.where(typical_price > typical_price.shift(1), raw_money_flow, 0), index=df_long.index)
                        neg_flow = pd.Series(np.where(typical_price < typical_price.shift(1), raw_money_flow, 0), index=df_long.index)
                        mfi = 100 - (100 / (1 + (pos_flow.rolling(14).sum() / (neg_flow.rolling(14).sum() + 1e-5))))
                        mfi_val = mfi.iloc[-1] if not pd.isna(mfi.iloc[-1]) else 50
                        
                        obv = np.where(df_long['Close'] > df_long['Close'].shift(1), df_long['Volume'], np.where(df_long['Close'] < df_long['Close'].shift(1), -df_long['Volume'], 0)).cumsum()
                        obv_ema = pd.Series(obv, index=df_long.index).ewm(span=20, adjust=False).mean()

                        # Gelişmiş teyitler: ADX, CMF, A/D, SuperTrend, VWAP ve çoklu zaman dilimi.
                        adx, plus_di, minus_di = adx_hesapla(df_long)
                        cmf, ad_line = cmf_hesapla(df_long)
                        supertrend, supertrend_line = supertrend_hesapla(df_long)
                        vwap = seans_vwap_hesapla(df_intraday)
                        mtf_detay, mtf_uyum = coklu_zaman_dilimi_analizi(df_intraday, df_long)
                        
                        para_durumu = f"Yoğun Para Girişi 🐋 (MFI:{mfi_val:.0f})" if mfi_val >= 70 else (f"Yoğun Para Çıkışı 📉 (MFI:{mfi_val:.0f})" if mfi_val <= 30 else f"Dengeli Akış ⚖️ (MFI:{mfi_val:.0f})")
                        if is_sig_tahta: para_durumu += " | Sığ Tahta ⚠️"

                        hacim_patlamasi_var = (hacim_oran >= 130) and (gunluk_degisim >= 4.0)

                        # --- HİBRİT SKOR: ESKİ CEZALI SKOR + GELİŞMİŞ TEYİT KATMANI ---
                        # Eski sistemin davranışı korunur: 50 puandan başlar; ana trend,
                        # EMA50, hacim/OBV, RSI, MACD ve Bollinger konumuna göre artar/azalır.
                        eski_skor = 50
                        skor_kalemleri = []

                        if uzun_vade_trend:
                            eski_skor += 15; skor_kalemleri.append(("Ana trend (SMA200)", 15))
                        else:
                            ceza = -5 if hacim_patlamasi_var else -25
                            eski_skor += ceza; skor_kalemleri.append(("Ana trend (SMA200)", ceza))

                        ema_50_val = df_long['Close'].ewm(span=50, adjust=False).mean().iloc[-1]
                        if bugun_kapanis > ema_50_val:
                            eski_skor += 10; skor_kalemleri.append(("EMA50 konumu", 10))
                        else:
                            eski_skor -= 15; skor_kalemleri.append(("EMA50 konumu", -15))

                        if hacim_oran >= 100 and obv[-1] > obv_ema.iloc[-1]:
                            eski_skor += 15; skor_kalemleri.append(("Hacim + OBV", 15))
                        else:
                            eski_skor -= 20; skor_kalemleri.append(("Hacim + OBV", -20))

                        if 35 <= rsi <= 55:
                            eski_skor += 10; skor_kalemleri.append(("RSI dengesi", 10))
                        elif rsi > 70:
                            eski_skor -= 15; skor_kalemleri.append(("RSI aşırı alım", -15))
                        else:
                            skor_kalemleri.append(("RSI dengesi", 0))

                        if macd_serisi.iloc[-1] > macd_sinyal.iloc[-1]:
                            eski_skor += 10; skor_kalemleri.append(("MACD teyidi", 10))
                        else:
                            eski_skor -= 10; skor_kalemleri.append(("MACD teyidi", -10))

                        if bugun_kapanis <= bb_mid:
                            eski_skor += 10; skor_kalemleri.append(("Bollinger konumu", 10))
                        elif bugun_kapanis >= bb_ust and rsi >= 65:
                            eski_skor -= 15; skor_kalemleri.append(("Bollinger şişkinliği", -15))
                        else:
                            skor_kalemleri.append(("Bollinger konumu", 0))

                        if is_sig_tahta:
                            eski_skor -= 20; skor_kalemleri.append(("Likidite / sığ tahta", -20))

                        eski_skor = int(min(100, max(0, eski_skor)))

                        # Yeni doğrulama katmanı: eski skoru değiştirmek yerine kontrollü
                        # bonus/ceza uygular. Böylece sevilen eski davranış korunur.
                        gelismis_bonus = 0
                        gelismis_ceza = 0
                        bonus_kalemleri = []
                        ceza_kalemleri = []

                        if adx >= 25 and plus_di > minus_di:
                            gelismis_bonus += 6; bonus_kalemleri.append(("ADX güçlü boğa trendi", 6))
                        elif adx < 18:
                            gelismis_ceza += 4; ceza_kalemleri.append(("ADX trend zayıf", -4))

                        if cmf > 0.05:
                            gelismis_bonus += 5; bonus_kalemleri.append(("CMF para girişi", 5))
                        elif cmf < -0.05:
                            gelismis_ceza += 5; ceza_kalemleri.append(("CMF para çıkışı", -5))

                        if supertrend == 1:
                            gelismis_bonus += 4; bonus_kalemleri.append(("SuperTrend yukarı", 4))
                        else:
                            gelismis_ceza += 4; ceza_kalemleri.append(("SuperTrend aşağı", -4))

                        if np.isfinite(vwap):
                            if bugun_kapanis > vwap:
                                gelismis_bonus += 3; bonus_kalemleri.append(("Fiyat VWAP üzerinde", 3))
                            else:
                                gelismis_ceza += 2; ceza_kalemleri.append(("Fiyat VWAP altında", -2))

                        mtf_etki = int(round((mtf_uyum - 50) * 0.10))
                        if mtf_etki > 0:
                            gelismis_bonus += mtf_etki; bonus_kalemleri.append(("Çoklu zaman dilimi uyumu", mtf_etki))
                        elif mtf_etki < 0:
                            gelismis_ceza += abs(mtf_etki); ceza_kalemleri.append(("Zaman dilimi çatışması", mtf_etki))

                        if pd.notna(sektorel_fark) and np.isfinite(float(sektorel_fark)):
                            if sektorel_fark > 0:
                                gelismis_bonus += 2; bonus_kalemleri.append(("Sektöre göre güçlü", 2))
                            else:
                                gelismis_ceza += 2; ceza_kalemleri.append(("Sektöre göre zayıf", -2))
                        # Referans verisi yoksa göreceli güç puanlamaya dahil edilmez.

                        # Gelişmiş katmanın etkisini sınırlayarak eski skoru baskın tutuyoruz.
                        gelismis_bonus = min(gelismis_bonus, 15)
                        gelismis_ceza = min(gelismis_ceza, 15)
                        skor = int(min(100, max(0, eski_skor + gelismis_bonus - gelismis_ceza)))

                        skor_aciklama = {
                            "eski_skor": eski_skor,
                            "bonus": gelismis_bonus,
                            "ceza": gelismis_ceza,
                            "nihai_skor": skor,
                            "eski_kalemler": skor_kalemleri,
                            "bonus_kalemler": bonus_kalemleri,
                            "ceza_kalemler": ceza_kalemleri,
                        }

                        skor_etiket = f"{skor} Puan (Güçlü 🟢)" if skor >= 70 else (f"{skor} Puan (Nötr ⚖️)" if skor >= 50 else f"{skor} Puan (Cezalı 🔴)")

                        # Destek/direnç referanslarında mevcut mumu hariç tutmak,
                        # henüz tamamlanmamış gün içi mumdan kaynaklanan ileriye bakış
                        # (look-ahead) etkisini azaltır.
                        gecmis_df = df_long.iloc[:-1] if len(df_long) > 1 else df_long
                        swing_high = gecmis_df['High'].tail(50).max()
                        swing_low = gecmis_df['Low'].tail(50).min()
                        tr = pd.concat([df_long['High'] - df_long['Low'], (df_long['High'] - df_long['Close'].shift()).abs(), (df_long['Low'] - df_long['Close'].shift()).abs()], axis=1).max(axis=1)
                        atr = tr[-14:].mean() if len(tr) >= 14 else bugun_kapanis * 0.02

                        # Tarihsel volatilite: günlük log getirilerin yıllıklandırılmış standart sapması.
                        log_getiriler = np.log(df_long['Close'] / df_long['Close'].shift(1)).replace([np.inf, -np.inf], np.nan).dropna()
                        hv20 = float(log_getiriler.tail(20).std(ddof=1) * np.sqrt(252)) if len(log_getiriler) >= 20 else 0.0
                        hv60 = float(log_getiriler.tail(60).std(ddof=1) * np.sqrt(252)) if len(log_getiriler) >= 30 else hv20
                        if not np.isfinite(hv20) or hv20 <= 0:
                            hv20 = float((atr / bugun_kapanis) * np.sqrt(252)) if bugun_kapanis > 0 else 0.20
                        if not np.isfinite(hv60) or hv60 <= 0:
                            hv60 = hv20

                        karma_destek = max([d for d in [swing_low, ema_50_val, bugun_kapanis - (atr * 2)] if pd.notna(d) and d < bugun_kapanis], default=bugun_kapanis - (atr * 1.5))
                        karma_direnc = min([dir_val for dir_val in [swing_high, bb_ust] if pd.notna(dir_val) and dir_val > bugun_kapanis], default=bugun_kapanis + (atr * 2.5))

                        # Teknik iptal seviyesi: fiyatın altındaki en yakın koruyucu ATR/Chandelier desteği.
                        chandelier_stop = gecmis_df['High'].tail(22).max() - (atr * 3)
                        stop_adaylari = [x for x in [chandelier_stop, bugun_kapanis - (atr * 1.5), karma_destek - (atr * 0.25)] if pd.notna(x) and x < bugun_kapanis]
                        trailing_stop = max(stop_adaylari, default=bugun_kapanis - (atr * 1.5))
                        risk_yuzde = (bugun_kapanis - trailing_stop) / max(bugun_kapanis, 1e-9) * 100
                        risk_seviyesi = 'YÜKSEK' if risk_yuzde > 7 or adx < 18 else ('DÜŞÜK' if risk_yuzde < 3.5 and adx >= 25 else 'ORTA')
                        vol_rejimi = volatilite_rejimi(bugun_kapanis, atr, hv20)

                        seviyeler = teknik_seviyeler_hesapla(df_long, bugun_kapanis, atr, ema_50_val, bb_alt, bb_mid, bb_ust, hv20)
                        tp1, tp2, tp3 = seviyeler['tp1'], seviyeler['tp2'], seviyeler['tp3']
                        karma_destek, karma_direnc = seviyeler['s1'], seviyeler['r1']
                        risk_odul = (tp2 - bugun_kapanis) / max(bugun_kapanis - trailing_stop, 1e-9)
                        hibrit_tp = f"TP1: {tp1:.2f} | TP2: {tp2:.2f} | TP3: {tp3:.2f}"

                        ema_9_val = df_long['Close'].ewm(span=9, adjust=False).mean().iloc[-1]
                        ema_21_val = df_long['Close'].ewm(span=21, adjust=False).mean().iloc[-1]
                        bb_ust_serisi = df_long['Close'].rolling(20).mean() + (df_long['Close'].rolling(20).std() * 2)
                        onceki_bb_ust = bb_ust_serisi.shift(1).iloc[-1]
                        kirilim_adaylari = [x for x in [swing_high, onceki_bb_ust] if pd.notna(x)]
                        kirilim_referansi = min(kirilim_adaylari, default=bugun_kapanis + atr)
                        breakout_kosulu = (bugun_kapanis >= kirilim_referansi) and (hacim_oran >= 120) and (ema_9_val > ema_21_val) and uzun_vade_trend

                        # Sinyal önceliği: önce kırılım ve risk/şişkinlik, ardından
                        # dipten dönüş ve trend adaylığı. Böylece aşırı alım durumu
                        # "uzun vadeli aday" etiketi tarafından gölgelenmez.
                        on_sinyal = "Nötr (İzle) ⚖️"
                        if breakout_kosulu:
                            on_sinyal = "YÜKSELİŞ KIRILIMI 🚀"
                        elif bugun_kapanis > bb_ust and rsi >= 68:
                            on_sinyal = "MOMENTUM AŞIRI ISINDI 🟡"
                        elif bugun_kapanis <= bb_alt and rsi <= 35 and uzun_vade_trend and (mfi_val <= 40 or gunluk_degisim > 0):
                            on_sinyal = "KUSURSUZ ALIM 🟢"
                        elif rsi <= 40 and uzun_vade_trend and bugun_kapanis <= bb_mid and bugun_kapanis <= (karma_destek + atr):
                            on_sinyal = "KADEMELİ ALIM 🔵"
                        elif uzun_vade_trend and skor >= 70:
                            on_sinyal = "UZUN VADELİ ADAY 🌟"
                        elif hacim_patlamasi_var and rsi < 50:
                            on_sinyal = "HACİMLİ TEPKİ 🟡"
                        elif not uzun_vade_trend:
                            on_sinyal = "KURTULUŞ ÇABASI 🧗" if (bugun_kapanis > ema_50_val) else "UZAK DUR! 🛑"
                            
                        if uzun_vade_trend: boga_sayisi += 1

                        alim_yonlu_on_sinyal = any(x in on_sinyal for x in ["ALIM", "KIRILIM", "ADAY"])
                        tetik_sonucu = {
                            "puan": 0, "seviye": "— UYGULANMAZ",
                            "mesaj": "— Giriş motoru değerlendirilmez: alım yönlü sinyal yok",
                            "detay": ["Giriş kalitesi yalnızca alım yönlü ön sinyallerde hesaplanır."],
                            "zaman_dilimleri": {}, "asama": "UYGULANMAZ",
                            "direnc": None, "hacim_orani": 0.0,
                            "rsi": None, "mum_kalitesi": 0.0, "sahte_kirilim": False,
                        }
                        mikro_teyit = tetik_sonucu["mesaj"]
                        if alim_yonlu_on_sinyal:
                            try:
                                df_5dk = df_intraday
                                if df_5dk is None or df_5dk.empty:
                                    df_5dk = tekil_taze_veri_cek(ticker)
                                tetik_sonucu = giris_motoru_hesapla(df_5dk, uzun_vade_trend)
                                mikro_teyit = tetik_sonucu["mesaj"]
                            except Exception as e:
                                izfin_hata_logla("giris_motoru", e, ticker)
                                mikro_teyit = "⚠️ Giriş motoru verisi alınamadı"

                        # Eski motor artık işlem kararı vermek yerine teknik PROFİL üretir.
                        # Yapı tanımları korunur; gerçek aksiyon tek merkezi motordan gelir.
                        profil_sinyali = nihai_karar_motoru(
                            on_sinyal, skor, int(tetik_sonucu.get("puan", 0)), bugun_kapanis,
                            ema_9_val, ema_21_val, ema_50_val, sma_200, rsi,
                            float(macd_serisi.iloc[-1]), float(macd_sinyal.iloc[-1]),
                            cmf, mfi_val, bb_ust, adx
                        )

                        panel_ek = {
                            'fiyat': float(bugun_kapanis), 'adx': adx, 'plus_di': plus_di, 'minus_di': minus_di,
                            'cmf': cmf, 'supertrend': supertrend, 'vwap': vwap, 'mtf_uyum': mtf_uyum,
                            'sektorel_fark': float(sektorel_fark), 'risk_odul': float(risk_odul),
                            'risk_seviyesi': risk_seviyesi
                        }
                        guven_skoru = sinyal_guven_skoru(panel_ek, skor)

                        merkezi_girdi = {
                            **panel_ek,
                            'profil': profil_sinyali, 'on_sinyal': on_sinyal,
                            'nihai_skor': int(skor),
                            'giris_puani': int(tetik_sonucu.get("puan", 0)),
                            'giris_asamasi': tetik_sonucu.get("asama", "YOK"),
                            'tetik_sahte_kirilim': bool(tetik_sonucu.get("sahte_kirilim", False)),
                            'guven_skoru': int(guven_skoru), 'volatilite_rejimi': vol_rejimi,
                            'ema9': float(ema_9_val), 'ema21': float(ema_21_val),
                            'ema50': float(ema_50_val), 'sma200': float(sma_200),
                            'rsi': float(rsi), 'mfi': float(mfi_val),
                            'macd': float(macd_serisi.iloc[-1]), 'macd_signal': float(macd_sinyal.iloc[-1]),
                            'bb_ust': float(bb_ust),
                        }
                        try:
                            merkezi_karar = merkezi_karar_motoru(merkezi_girdi)
                        except Exception as e:
                            # Merkezi katman hiçbir zaman veri taramasını düşürmemeli.
                            # Hata loglanır, varlık eski teknik profille görünmeye devam eder.
                            izfin_hata_logla("merkezi_karar_motoru", e, ticker)
                            merkezi_karar = {
                                'karar': 'İZLE / TEYİT BEKLE 🟡',
                                'aksiyon': 'IZLE',
                                'profil': profil_sinyali,
                                'guven': int(guven_skoru),
                                'risk': risk_seviyesi,
                                'mtf_uyum': int(mtf_uyum),
                                'giris_puani': int(tetik_sonucu.get("puan", 0) or 0),
                                'hibrit_skor': int(skor),
                                'olumlu': [],
                                'olumsuz': ['merkezi karar katmanında hesaplama hatası; güvenli izleme moduna geçildi'],
                                'ozet': 'Karar katmanı hata verdiği için varlık taramadan atılmadı; güvenli izleme modu kullanıldı.'
                            }
                        sinyal = merkezi_karar['karar']
                        if merkezi_karar.get('aksiyon') in {'GUCLU_AL', 'AL', 'ERKEN_AL'}:
                            alim_firsati += 1

                        gecici_teknik_paneller[ticker] = {
                            "ticker": ticker, "fiyat": float(bugun_kapanis), "gunluk_degisim": float(gunluk_degisim),
                            "ema9": float(ema_9_val), "ema21": float(ema_21_val), "ema50": float(ema_50_val), "sma200": float(sma_200),
                            "rsi": float(rsi), "mfi": float(mfi_val), "macd": float(macd_serisi.iloc[-1]), "macd_signal": float(macd_sinyal.iloc[-1]),
                            "atr": float(atr), "hv20": float(hv20), "hv60": float(hv60), "obv": float(obv[-1]), "obv_ema": float(obv_ema.iloc[-1]),
                            "bb_alt": float(bb_alt), "bb_mid": float(bb_mid), "bb_ust": float(bb_ust),
                            "destek": float(karma_destek), "direnc": float(karma_direnc), "stop": float(trailing_stop),
                            "tp1": float(tp1), "tp2": float(tp2), "tp3": float(tp3), "swing_low": float(swing_low), "swing_high": float(swing_high),
                            "s1": float(seviyeler["s1"]), "s2": float(seviyeler["s2"]), "s3": float(seviyeler["s3"]),
                            "r1": float(seviyeler["r1"]), "r2": float(seviyeler["r2"]), "r3": float(seviyeler["r3"]),
                            "tp1_yildiz": int(seviyeler["tp1_yildiz"]), "tp2_yildiz": int(seviyeler["tp2_yildiz"]), "tp3_yildiz": int(seviyeler["tp3_yildiz"]),
                            "hacim": float(bugun_hacim), "hacim_ort": float(hacim_sma20), "hacim_oran": float(hacim_oran),
                            "sektorel_fark": float(sektorel_fark), "sinyal": sinyal, "profil": profil_sinyali, "on_sinyal": on_sinyal, "merkezi_karar": merkezi_karar, "veri_kaynagi": veri_kaynagi, "teyit": mikro_teyit,
                            "tetik_puani": int(tetik_sonucu.get("puan", 0)), "tetik_seviyesi": tetik_sonucu.get("seviye", "⏳ TETİK YOK"),
                            "tetik_detay": tetik_sonucu.get("detay", []), "tetik_direnc": tetik_sonucu.get("direnc"),
                            "tetik_hacim_orani": float(tetik_sonucu.get("hacim_orani", 0.0)), "tetik_rsi": tetik_sonucu.get("rsi"),
                            "tetik_mum_kalitesi": float(tetik_sonucu.get("mum_kalitesi", 0.0)), "tetik_sahte_kirilim": bool(tetik_sonucu.get("sahte_kirilim", False)),
                            "giris_puani": int(tetik_sonucu.get("puan", 0)), "giris_seviyesi": tetik_sonucu.get("seviye", "⏳ GİRİŞ UYGUN DEĞİL"),
                            "giris_asamasi": tetik_sonucu.get("asama", "YOK"), "giris_zaman_dilimleri": tetik_sonucu.get("zaman_dilimleri", {}),
                            "giris_detay": tetik_sonucu.get("detay", []),
                            "adx": float(adx), "plus_di": float(plus_di), "minus_di": float(minus_di), "cmf": float(cmf), "ad_line": float(ad_line),
                            "supertrend": int(supertrend), "supertrend_line": float(supertrend_line), "vwap": float(vwap) if np.isfinite(vwap) else np.nan,
                            "mtf_detay": mtf_detay, "mtf_uyum": int(mtf_uyum), "guven_skoru": int(guven_skoru),
                            "risk_odul": float(risk_odul), "risk_yuzde": float(risk_yuzde), "risk_seviyesi": risk_seviyesi, "volatilite_rejimi": vol_rejimi,
                            "sinyal_yonu": sinyal_yonu_belirle(sinyal), "cezali_skor": int(skor), "nihai_skor": int(skor),
                            "eski_cezali_skor": int(eski_skor), "skor_bonus": int(gelismis_bonus),
                            "skor_ceza": int(gelismis_ceza), "skor_aciklama": skor_aciklama,
                            "seans_disi": seans_disi_metin, "seans_disi_fiyat": seans_disi_fiyat
                        }

                        gecici_sozlu_analizler[ticker] = sozlu_teknik_analiz_olustur(
                            ticker=ticker, fiyat=bugun_kapanis, gunluk_degisim=gunluk_degisim,
                            rsi=float(rsi), macd=float(macd_serisi.iloc[-1]), macd_sinyal=float(macd_sinyal.iloc[-1]),
                            ema9=float(ema_9_val), ema21=float(ema_21_val), ema50=float(ema_50_val), sma200=float(sma_200),
                            bb_alt=float(bb_alt), bb_mid=float(bb_mid), bb_ust=float(bb_ust),
                            hacim_oran=float(hacim_oran), mfi=float(mfi_val), sektorel_fark=float(sektorel_fark),
                            destek=float(karma_destek), direnc=float(karma_direnc), stop=float(trailing_stop),
                            tp1=float(tp1), tp2=float(tp2), tp3=float(tp3), sinyal=sinyal, veri_kaynagi=veri_kaynagi
                        )

                        peg_degeri = peg_haritasi.get(ticker)
                        peg_sayi, peg_etiket = peg_yorumu(peg_degeri)
                        peg_gosterim = f"{peg_sayi} · {peg_etiket}" if peg_degeri is not None else peg_etiket
                        gecici_teknik_paneller[ticker]["peg"] = float(peg_degeri) if peg_degeri is not None else None
                        gecici_teknik_paneller[ticker]["peg_etiket"] = peg_etiket

                        gecici_sonuclar.append({
                            "Varlık": ticker, "Fiyat": fiyat_str, "Görec. Güç (Sektör)": gorec_guc_str,
                            "Gelişmiş Skor": skor_etiket, "Güven": f"%{guven_skoru}", "MTF Uyum": f"%{mtf_uyum}", "Risk": risk_seviyesi, "Para Akışı": para_durumu,
                            "PEG / Değerleme": peg_gosterim, "Teknik Profil": profil_sinyali, "Nihai Sinyal": sinyal, "🎯 Giriş Kalitesi": mikro_teyit,
                            "Seans Dışı": seans_disi_metin, "Veri Kaynağı": veri_kaynagi,
                            "Karma Destek": f"{karma_destek:.2f}", "Karma Direnç": f"{karma_direnc:.2f}",
                            "Süren Stop": f"{trailing_stop:.2f}", "Teknik Hedefler": hibrit_tp
                        })
                    except Exception as e:
                        izfin_hata_logla("ana_tarama", e, ticker)
                        basarisi_cekilemeyen_varliklar.append(ticker)
                        continue

                ilerleme.progress(1.0, text="Tarama tamamlandı")
                st.session_state.sonuclar = gecici_sonuclar
                st.session_state.sozlu_analizler = gecici_sozlu_analizler
                st.session_state.teknik_paneller = gecici_teknik_paneller
                st.session_state.basarisiz_taramalar = basarisi_cekilemeyen_varliklar
                st.session_state.boga_sayisi = boga_sayisi
                st.session_state.alim_firsati = alim_firsati
                st.session_state.tarama_durumu = True
                try:
                    sinyal_kayitlarini_firestore_yaz(gecici_sonuclar, gecici_teknik_paneller)
                    performans_cache_gecersiz_kil()
                except Exception as e:
                    izfin_hata_logla("sinyal_firestore_yaz", e)

    if aktif_sayfa == "🔎 Akıllı Tarama" and st.session_state.tarama_durumu:
        if st.session_state.basarisiz_taramalar:
            st.warning(f"⚠️ Veri/hesaplama sorunu nedeniyle es geçilen varlıklar: **{', '.join(st.session_state.basarisiz_taramalar)}**")
        if st.session_state.get("taramada_hatalar"):
            tipler = {}
            for h in st.session_state.taramada_hatalar:
                tip = h.get("tip", "Hata")
                tipler[tip] = tipler.get(tip, 0) + 1
            st.caption("Teknik hata özeti (ayrıntılar Streamlit Cloud loglarında): " + " · ".join(f"{k}: {v}" for k, v in sorted(tipler.items())))
            ornek_hatalar = st.session_state.taramada_hatalar[:5]
            if ornek_hatalar:
                st.caption("İlk hata bağlamları: " + " · ".join(
                    f"{h.get('ticker') or 'genel'} / {h.get('baglam','?')} / {h.get('tip','Hata')}: {h.get('mesaj','')}" for h in ornek_hatalar
                ))
            
        if not st.session_state.sonuclar:
            st.error("❌ Veriler çekilemedi. Yukarıdaki Tarama Evreni bölümünden farklı bir profil veya varlık grubu seçip tekrar deneyin.")
        else:
            col1, col2, col3 = st.columns(3)
            with col1: st.markdown(f"""<div class="kpi-card"><div class="kpi-title">Taranan Varlık</div><div class="kpi-value">{len(st.session_state.sonuclar)}</div></div>""", unsafe_allow_html=True)
            with col2: st.markdown(f"""<div class="kpi-card"><div class="kpi-title">Boğa Trendinde (200G)</div><div class="kpi-value kpi-highlight-green">{st.session_state.boga_sayisi}</div></div>""", unsafe_allow_html=True)
            with col3: st.markdown(f"""<div class="kpi-card"><div class="kpi-title">Alım Fırsatları & Kırılımlar</div><div class="kpi-value kpi-highlight-fire">{"🔥 " + str(st.session_state.alim_firsati)}</div></div>""", unsafe_allow_html=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
            sadece_alim_goster = st.checkbox("🎯 Sadece Merkezi Motorun AL Sinyallerini Göster", value=False)
            
            df_sonuc = pd.DataFrame(st.session_state.sonuclar)
            if sadece_alim_goster:
                df_sonuc = df_sonuc[df_sonuc["Nihai Sinyal"].apply(lambda x: sinyal_yonu_belirle(x) == "ALIM")]
            
            def color_df(row):
                c = ''
                if any(x in str(row['Nihai Sinyal']) for x in ['🟢', '🔵', '🚀', '🌟']): c = 'background-color: rgba(39, 174, 96, 0.15)'
                elif any(x in str(row['Nihai Sinyal']) for x in ['🟡', '🟠']): c = 'background-color: rgba(243, 156, 18, 0.2)'
                elif any(x in str(row['Nihai Sinyal']) for x in ['🛑', '🔴']): c = 'background-color: rgba(192, 57, 43, 0.15)'
                return [c] * len(row)

            if not df_sonuc.empty:
                if "izfin_scan_table_focus" not in st.session_state:
                    st.session_state.izfin_scan_table_focus = False

                # v1.7.26 — Tarama tablosu odak / geniş ekran modu
                if st.session_state.izfin_scan_table_focus:
                    st.markdown(
                        """
                        <style>
                        [data-testid="stSidebar"]{display:none!important;}
                        [data-testid="stHeader"]{display:none!important;}
                        [data-testid="stToolbar"]{display:none!important;}
                        footer{display:none!important;}
                        .stAppViewContainer .main .block-container{
                            max-width:100%!important;
                            width:100%!important;
                            padding:18px 22px 34px!important;
                        }
                        .iz-signals,.iz-scan-table-wrap{
                            width:100%!important;
                            max-width:none!important;
                        }
                        .iz-scan-table-wrap{
                            min-height:calc(100vh - 150px)!important;
                        }
                        .iz-scan-table-wrap table{
                            width:100%!important;
                            font-size:13px!important;
                        }
                        </style>
                        """,
                        unsafe_allow_html=True,
                    )

                    focus_h1, focus_h2 = st.columns([6.8, 1.2], vertical_alignment="center")
                    with focus_h1:
                        st.markdown(
                            """
                            <div class="iz-focus-title">
                                <div>
                                    <small>IZFIN SIGNATURE SCAN</small>
                                    <h2>Akıllı Tarama Sonuçları</h2>
                                    <p>Geniş tablo görünümü · tüm karar alanları tek ekranda</p>
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                    with focus_h2:
                        if st.button(
                            "↙ Geniş Görünümden Çık",
                            key="scan_table_focus_exit",
                            use_container_width=True,
                            type="secondary",
                        ):
                            st.session_state.izfin_scan_table_focus = False
                            st.rerun()

                    st.markdown(
                        f'<div class="iz-focus-meta"><span>{len(df_sonuc)} varlık</span>'
                        f'<span>{"Yalnızca AL sinyalleri" if sadece_alim_goster else "Tüm merkezi kararlar"}</span></div>',
                        unsafe_allow_html=True,
                    )

                    st.markdown(
                        '<div class="iz-scan-table-wrap">'
                        + izfin_tarama_tablosu_html(df_sonuc)
                        + '</div>',
                        unsafe_allow_html=True,
                    )
                    st.stop()

                title_col, action_col = st.columns([5.7, 1.3], vertical_alignment="center")
                with title_col:
                    st.markdown("### Akıllı Tarama Sonuçları")
                    st.caption("Ana tablo karar vermeyi kolaylaştıran temel alanları gösterir; ayrıntılı teknik panel aşağıda açılır.")
                with action_col:
                    if st.button(
                        "⛶ Tabloyu Genişlet",
                        key="scan_table_focus_open",
                        use_container_width=True,
                        type="secondary",
                        help="Tarama tablosunu dikkat dağıtan paneller olmadan geniş görünümde aç.",
                    ):
                        st.session_state.izfin_scan_table_focus = True
                        st.rerun()

                st.markdown(
                    '<div class="iz-scan-table-wrap">'
                    + izfin_tarama_tablosu_html(df_sonuc)
                    + '</div>',
                    unsafe_allow_html=True,
                )

                peg_degerlendirilemeyenler = [
                    str(v) for v in df_sonuc.loc[
                        df_sonuc.get("PEG / Değerleme", pd.Series(index=df_sonuc.index, dtype=str)).astype(str).str.contains("değerlendirilemedi", case=False, na=False),
                        "Varlık"
                    ].tolist()
                ] if "PEG / Değerleme" in df_sonuc.columns else []
                if peg_degerlendirilemeyenler:
                    st.caption(
                        "ℹ️ PEG değeri alınamayan veya anlamlı olmayan varlıklar: "
                        + ", ".join(peg_degerlendirilemeyenler)
                        + ". Bu durum teknik analiz ve skorlamayı etkilemez; PEG yalnızca ayrı bir temel değerleme göstergesidir."
                    )
                
                st.markdown('<div id="izfin-detail-anchor"></div>', unsafe_allow_html=True)
                st.markdown("### 📊 Detaylı Teknik Analiz & Gösterge Paneli")
                _detay_options = df_sonuc["Varlık"].tolist()
                _pending_detail = st.session_state.pop("izfin_pending_detail_ticker", None)
                if _pending_detail in _detay_options:
                    st.session_state["detay_hisse_secici"] = _pending_detail
                elif st.session_state.get("detay_hisse_secici") not in _detay_options and _detay_options:
                    st.session_state["detay_hisse_secici"] = _detay_options[0]

                secilen_detay_hisse = st.selectbox(
                    "İncelemek İçin Varlık Seçin:",
                    options=_detay_options,
                    key="detay_hisse_secici",
                )

                if secilen_detay_hisse:
                    if st.session_state.pop("izfin_scroll_to_detail", False):
                        components.html(
                            """
                            <script>
                            setTimeout(() => {
                              const p = window.parent.document.getElementById('izfin-detail-anchor');
                              if (p) p.scrollIntoView({behavior:'smooth', block:'start'});
                            }, 180);
                            </script>
                            """,
                            height=0,
                        )
                    st.markdown(
                        f"""
                        <div class="iz-detail-active-stock">
                            <small>AKTİF DETAY ANALİZİ</small>
                            <strong>{html.escape(str(secilen_detay_hisse))}</strong>
                            <span>Teknik panel · skor · giriş kalitesi · risk · hedefler</span>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    panel_verisi = st.session_state.teknik_paneller.get(secilen_detay_hisse)
                    if panel_verisi:
                        st.markdown(gelismis_teknik_panel_olustur(panel_verisi), unsafe_allow_html=True)

                        with st.expander("🧮 Skor nasıl oluştu?", expanded=False):
                            eski_v = int(panel_verisi.get("eski_cezali_skor", panel_verisi.get("cezali_skor", 50)))
                            bonus_v = int(panel_verisi.get("skor_bonus", 0))
                            ceza_v = int(panel_verisi.get("skor_ceza", 0))
                            nihai_v = int(panel_verisi.get("cezali_skor", eski_v + bonus_v - ceza_v))
                            s1, s2, s3, s4 = st.columns(4)
                            s1.metric("Eski Cezalı Skor", eski_v)
                            s2.metric("Gelişmiş Bonus", f"+{bonus_v}")
                            s3.metric("Gelişmiş Ceza", f"-{ceza_v}")
                            s4.metric("Nihai Skor", nihai_v)

                            aciklama = panel_verisi.get("skor_aciklama", {})
                            sol, sag = st.columns(2)
                            with sol:
                                st.markdown("**Eski sistem kalemleri**")
                                for ad, deger in aciklama.get("eski_kalemler", []):
                                    st.write(f"{ad}: {deger:+d}")
                                st.markdown("**Bonuslar**")
                                if aciklama.get("bonus_kalemler"):
                                    for ad, deger in aciklama.get("bonus_kalemler", []):
                                        st.write(f"{ad}: +{deger}")
                                else:
                                    st.caption("Ek bonus oluşmadı.")
                            with sag:
                                st.markdown("**Cezalar**")
                                if aciklama.get("ceza_kalemler"):
                                    for ad, deger in aciklama.get("ceza_kalemler", []):
                                        st.write(f"{ad}: {deger}")
                                else:
                                    st.caption("Ek ceza oluşmadı.")
                                st.info("Nihai skor = eski cezalı skor + sınırlı gelişmiş bonus − sınırlı gelişmiş ceza")

                        karar = karar_motoru_ozeti(panel_verisi)
                        st.markdown("### 🧠 Şeffaf Karar Motoru")
                        k1,k2,k3,k4 = st.columns(4)
                        k1.metric("Karar", karar['karar'])
                        k2.metric("Algoritma Güveni", f"%{karar['guven']}")
                        k3.metric("Risk", karar['risk'])
                        k4.metric("MTF Uyum", f"%{panel_verisi.get('mtf_uyum',50)}")
                        st.markdown(f"**Olumlu teyitler:** {', '.join(karar['olumlu']) or 'Yeterli teyit yok'}  \n**Riskler:** {', '.join(karar['olumsuz']) or 'Belirgin ek risk yok'}")
                        mtf = panel_verisi.get('mtf_detay', {})
                        if mtf:
                            st.caption(" · ".join([f"{k}: {v.get('yon')}" for k,v in mtf.items()]))
                        hisse_satiri = df_sonuc[df_sonuc["Varlık"] == secilen_detay_hisse]
                        anlik_sinyal = hisse_satiri["Nihai Sinyal"].values[0] if not hisse_satiri.empty else "Nötr (İzle)"
                        anlik_teyit = hisse_satiri["🎯 Giriş Kalitesi"].values[0] if not hisse_satiri.empty else ""
                        st.markdown(aksiyon_rehberi_olustur(anlik_sinyal, anlik_teyit, panel_verisi.get('profil'), karar), unsafe_allow_html=True)
                    else:
                        st.info("Bu varlık için teknik panel verisi bulunamadı. Derin taramayı yeniden çalıştırın.")


if aktif_sayfa == "🎯 Projeksiyon & Senaryo":
    st.markdown(
        """
        <div class="iz-proj-hero">
            <div>
                <div class="iz-section-label">IZFIN PROJECTION LAB</div>
                <h2>Projeksiyon & Senaryo Analizi</h2>
                <p>Seçilen varlık için yaklaşık 45 günlük hareket bandını, model uyumunu ve yukarı/aşağı teknik senaryoları tek ekranda inceleyin.</p>
            </div>
            <span class="iz-badge wait">45G MODEL</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not st.session_state.tarama_durumu or not st.session_state.teknik_paneller:
        st.markdown(
            """
            <div class="iz-proj-empty">
                <b>Önce Akıllı Tarama çalıştırılmalı</b>
                <span>Projeksiyon motoru, son taramada oluşan teknik panel verilerini kullanır.</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button(
            "Akıllı Tarama Merkezine Git",
            type="primary",
            use_container_width=True,
            key="projection_to_scan",
        ):
            _izfin_nav_to("🔎 Akıllı Tarama")
            st.rerun()
    else:
        varliklar = list(st.session_state.teknik_paneller.keys())

        top_left, top_right = st.columns([1.15, .85], gap="large")
        with top_left:
            secilen_opsiyon = st.selectbox(
                "Projeksiyon yapılacak varlık",
                varliklar,
                key="opsiyon_varlik_secimi",
            )
        with top_right:
            st.markdown(
                """
                <div class="iz-proj-model-note">
                    <small>MODEL</small>
                    <b>ATR + Tarihsel Volatilite</b>
                    <span>45 günlük karma fiyat hareket bandı</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

        panel = st.session_state.teknik_paneller.get(secilen_opsiyon, {})
        proj = opsiyon_projeksiyonu_hesapla(panel, gun=45)

        if not proj:
            st.error("Projeksiyon için yeterli fiyat verisi bulunamadı.")
        else:
            st.markdown('<div class="iz-proj-section-title">Model Karşılaştırması</div>', unsafe_allow_html=True)

            o1, o2, o3, o4 = st.columns(4)
            o1.metric("Güncel Fiyat", f"{proj['fiyat']:.2f}")
            o2.metric("ATR Modeli", f"±{proj['atr_hareket']:.2f}", f"%{proj['atr_yuzde']:.1f}")
            o3.metric("Volatilite Modeli", f"±{proj['volatilite_hareket']:.2f}", f"%{proj['volatilite_yuzde']:.1f}")
            o4.metric("Karma Model", f"±{proj['karma_hareket']:.2f}", f"%{proj['karma_yuzde']:.1f}")

            b1, b2, b3 = st.columns(3)
            b1.metric("45G Karma Bant", f"{proj['alt_1s']:.2f} / {proj['ust_1s']:.2f}")
            b2.metric("Geniş Risk Bandı", f"{proj['alt_2s']:.2f} / {proj['ust_2s']:.2f}")
            b3.metric("Model Güven Skoru", f"%{proj['guven_skoru']}", f"Uyum %{proj['model_uyumu']*100:.0f}")

            st.progress(proj['guven_skoru'] / 100)
            st.caption(
                f"20 günlük yıllıklandırılmış volatilite: %{proj['hv20']*100:.1f} · "
                f"60 günlük: %{proj['hv60']*100:.1f} · Karma: %{proj['hv_karma']*100:.1f}"
            )

            sinyal = panel.get("sinyal", "Nötr")
            destek = float(panel.get("destek", proj['alt_1s']))
            direnc = float(panel.get("direnc", proj['ust_1s']))
            stop = float(panel.get("stop", proj['alt_1s']))
            tp1 = float(panel.get("tp1", proj['ust_1s']))
            tp2 = float(panel.get("tp2", proj['ust_2s']))

            st.markdown('<div class="iz-proj-section-title">Teknik Senaryolar</div>', unsafe_allow_html=True)

            al_col, sat_col = st.columns(2, gap="large")

            with al_col:
                _up_html = (
                    f'<div class="iz-scenario-card iz-scenario-up">'
                    f'<div class="iz-scenario-head"><span class="iz-scenario-dot"></span><div>'
                    f'<small>POZİTİF SENARYO</small><h3>Yükseliş / Alım Senaryosu</h3></div></div>'
                    f'<div class="iz-scenario-row"><span>Tetik</span>'
                    f'<b>{direnc:.2f} üzeri kalıcılık + RSI 50 üstü + MACD yukarı kesişim</b></div>'
                    f'<div class="iz-scenario-row"><span>Teknik hedefler</span>'
                    f'<b>{tp1:.2f} → {tp2:.2f}</b></div>'
                    f'<div class="iz-scenario-row"><span>Karma model üst bantları</span>'
                    f'<b>{proj["ust_1s"]:.2f} → {proj["ust_2s"]:.2f}</b></div>'
                    f'<div class="iz-scenario-row"><span>Risk iptali / stop</span>'
                    f'<b>{stop:.2f}</b></div>'
                    f'</div>'
                )
                st.markdown(_up_html, unsafe_allow_html=True)

            with sat_col:
                _down_html = (
                    f'<div class="iz-scenario-card iz-scenario-down">'
                    f'<div class="iz-scenario-head"><span class="iz-scenario-dot"></span><div>'
                    f'<small>NEGATİF SENARYO</small><h3>Düşüş / Satış Baskısı</h3></div></div>'
                    f'<div class="iz-scenario-row"><span>Tetik</span>'
                    f'<b>{destek:.2f} altı kapanış + RSI 40 altı veya MACD negatifliğinin güçlenmesi</b></div>'
                    f'<div class="iz-scenario-row"><span>Karma model aşağı bantları</span>'
                    f'<b>{proj["alt_1s"]:.2f} → {proj["alt_2s"]:.2f}</b></div>'
                    f'<div class="iz-scenario-row"><span>Senaryo geçersizliği</span>'
                    f'<b>{direnc:.2f} üzeri kalıcılık</b></div>'
                    f'</div>'
                )
                st.markdown(_down_html, unsafe_allow_html=True)

            yon = sinyal_yonu_belirle(sinyal)
            model_farki = abs(proj['atr_yuzde'] - proj['volatilite_yuzde'])

            if model_farki <= 3:
                model_yorumu = "ATR ve volatilite modelleri birbirine yakın; hareket tahmini görece tutarlı."
            elif proj['volatilite_yuzde'] > proj['atr_yuzde']:
                model_yorumu = "Tarihsel volatilite, güncel ATR'den daha geniş hareket ihtimali gösteriyor; ani fiyat genişlemelerine karşı temkinli olunmalı."
            else:
                model_yorumu = "Güncel ATR, tarihsel volatiliteden daha yüksek; kısa vadede olağandışı hareketlilik yaşanıyor olabilir."

            yon_class = "neutral"
            yon_title = "Dengeli / İzle"
            if yon == "ALIM":
                yon_class = "up"
                yon_title = "Yükseliş öncelikli"
            elif yon == "SATIŞ":
                yon_class = "down"
                yon_title = "Sermaye koruma öncelikli"

            _direction_html = (
                f'<div class="iz-direction-card iz-direction-{yon_class}">'
                f'<div><small>ALGORİTMİK YÖN ÖZETİ</small><h3>{yon_title}</h3></div>'
                f'<p><b>Mevcut sistem sinyali:</b> {html.escape(str(sinyal))}. '
                f'{html.escape(model_yorumu)} Güven skoru %{proj["guven_skoru"]}.</p>'
                f'</div>'
            )
            st.markdown(_direction_html, unsafe_allow_html=True)

            st.caption(
                "Bu bölüm gerçek opsiyon zinciri veya implied volatility kullanmaz. ATR + tarihsel volatilite "
                "tabanlı fiyat hareketi tahminidir; güven skoru istatistiksel olasılık değil, model uyum göstergesidir."
            )


if aktif_sayfa == "📊 Takip & Performans":
    st.subheader("📊 Takip & Performans")
    st.markdown(
        "Her hissede **ilk alım sinyali tarihi ve fiyatı sabit tutulur**. "
        "Aynı alım dönemi devam ederken sinyal türü değişse bile yeni kayıt açılmaz; "
        "performans ilk giriş fiyatından güncel fiyata göre hesaplanır."
    )

    if not st.session_state.user_email or not db:
        st.warning("Bu bölüm için Firebase bağlantısı ve kullanıcı oturumu gereklidir.")
    else:
        col_p1, col_p2 = st.columns([1, 3])
        with col_p1:
            guncelle_tiklandi = st.button("🔄 Güncel Fiyatları Yenile", use_container_width=True)
        with col_p2:
            st.caption(
                "Sinyal kaybolursa pozisyon kapanır. Aynı hissede daha sonra yeniden alım oluşursa yeni dönem başlatılır."
            )

        with st.expander("🧹 Geçmiş kayıt bakımı", expanded=False):
            st.caption("Eski sürümlerin oluşturduğu gerçek mükerrer Firestore belgelerini temizler. Silmeden önce her belge sinyal_arsivi_temizlik_yedegi koleksiyonuna kopyalanır.")
            temizlik_onay = st.checkbox("Yedek alındıktan sonra mükerrer kayıtların silinmesini onaylıyorum.", key="gecmis_kayit_temizlik_onay")
            if st.button("🧹 Mükerrerleri Yedekle ve Temizle", disabled=not temizlik_onay):
                with st.spinner("Geçmiş kayıtlar kontrol ediliyor..."):
                    temiz_ozet = gecmis_mukerrer_kayitlari_temizle()
                    performans_cache_gecersiz_kil()
                st.success(f"Temizlik tamamlandı: {temiz_ozet['grup']} mükerrer grup · {temiz_ozet['yedeklenen']} yedek · {temiz_ozet['silinen']} silinen belge.")

        kayitlar = performans_kayitlarini_getir()
        # Tüm performans ekranı aynı temiz kayıt setini kullanır.
        # Böylece aktif tablo, kapanmış geçmiş ve IZFIN Karnesi aynı hisseyi
        # aynı alım dönemi için tekrar tekrar göstermez.
        kayitlar = performans_kayitlarini_tekillestir(kayitlar)

        if guncelle_tiklandi and kayitlar:
            with st.spinner("Açık alım kayıtları güncel fiyatlarla karşılaştırılıyor..."):
                kayitlar = performans_fiyatlarini_guncelle(kayitlar)
                performans_cache_gecersiz_kil()
                kayitlar = performans_kayitlarini_tekillestir(kayitlar)
            st.success("Güncel fiyatlar yenilendi.")

        if not kayitlar:
            st.info(
                "Henüz takip edilen bir alım pozisyonu yok. İlk ALIM, KIRILIM veya ADAY sinyali oluştuğunda burada görüntülenecek."
            )
        else:
            df_perf = pd.DataFrame(kayitlar).reset_index(drop=True)
            for col in ["giris_fiyati", "son_fiyat", "kapanis_fiyati", "getiri_yuzde"]:
                if col in df_perf.columns:
                    df_perf[col] = pd.to_numeric(df_perf[col], errors="coerce")

            if "durum" not in df_perf.columns:
                df_perf["durum"] = "ACIK"
            df_perf["durum"] = (
                df_perf["durum"].fillna("ACIK")
                .replace({"None": "ACIK", "": "ACIK"})
                .astype(str).str.upper()
            )
            df_perf["_tarih"] = pd.to_datetime(df_perf.get("olusturma_zamani"), errors="coerce")
            df_perf["_kapanis_tarih"] = pd.to_datetime(df_perf.get("kapanis_zamani"), errors="coerce")

            # Ana tabloda her hisse için yalnızca en eski ilk alım kaydı tutulur.
            # Böylece eski sürümlerden kalan mükerrer açık belgeler ekranda çoğalmaz.
            acik_df = df_perf[df_perf["durum"].eq("ACIK")].copy()
            if not acik_df.empty:
                acik_df["ticker"] = acik_df["ticker"].fillna("").astype(str).str.strip().str.upper()
            acik_df = (
                acik_df.sort_values(["ticker", "_tarih"], ascending=[True, True])
                .drop_duplicates(subset=["ticker"], keep="first")
                .sort_values("_tarih", ascending=False)
                .reset_index(drop=True)
            )
            kapali_df = df_perf[df_perf["durum"].eq("KAPALI")].copy()
            if not kapali_df.empty:
                kapali_df["_giris_gun"] = kapali_df["_tarih"].dt.floor("D")
                kapali_df["_kapanis_gun"] = kapali_df["_kapanis_tarih"].dt.floor("D")
                kapali_df["_giris_fiyat_key"] = pd.to_numeric(
                    kapali_df.get("giris_fiyati"), errors="coerce"
                ).round(4)
                kapali_df["_doluluk"] = kapali_df.notna().sum(axis=1)
                kapali_df = (
                    kapali_df
                    .sort_values(
                        ["_doluluk", "_kapanis_tarih", "_tarih"],
                        ascending=[False, False, True],
                        na_position="last"
                    )
                    .drop_duplicates(
                        subset=["ticker", "_giris_gun", "_giris_fiyat_key", "_kapanis_gun"],
                        keep="first"
                    )
                    .sort_values(["_kapanis_tarih", "_tarih"], ascending=False)
                    .drop(columns=["_giris_gun", "_kapanis_gun", "_giris_fiyat_key", "_doluluk"], errors="ignore")
                    .reset_index(drop=True)
                )

            simdi_ts = pd.Timestamp.now(tz=None)

            def naive_tarih(seri):
                if seri.empty:
                    return seri
                return seri.dt.tz_localize(None) if getattr(seri.dt, "tz", None) is not None else seri

            acik_tarih = naive_tarih(acik_df["_tarih"]) if not acik_df.empty else pd.Series(dtype="datetime64[ns]")
            acik_gecen = ((simdi_ts.normalize() - acik_tarih.dt.normalize()).dt.days.clip(lower=0)
                           if not acik_df.empty else pd.Series(dtype=float))

            pozitif = int((acik_df.get("getiri_yuzde", pd.Series(dtype=float)) > 0).sum())
            negatif = int((acik_df.get("getiri_yuzde", pd.Series(dtype=float)) < 0).sum())
            ort_getiri = float(acik_df["getiri_yuzde"].mean()) if not acik_df.empty else 0.0

            kp1, kp2, kp3, kp4 = st.columns(4)
            kp1.metric("Aktif Hisse", int(len(acik_df)))
            kp2.metric("Kârda / Zararda", f"{pozitif} / {negatif}")
            kp3.metric("Ort. Açık Performans", f"%{ort_getiri:+.1f}")
            kp4.metric("Kapanmış Dönem", int(len(kapali_df)))

            def performans_hucre_stili(val):
                if pd.isna(val):
                    return ""
                if val > 0:
                    return "background-color: rgba(39,174,96,0.18); font-weight:700;"
                if val < 0:
                    return "background-color: rgba(231,76,60,0.18); font-weight:700;"
                return "background-color: rgba(149,165,166,0.10); font-weight:600;"

            def tablo_stili(df_gorunum):
                return (
                    df_gorunum.style
                    .format({
                        "İlk Alım Fiyatı": "{:.2f}",
                        "Güncel Fiyat": "{:.2f}",
                        "Kapanış Fiyatı": "{:.2f}",
                        "İlk Stop": "{:.2f}", "İlk TP1": "{:.2f}", "İlk TP2": "{:.2f}", "İlk TP3": "{:.2f}",
                        "Kâr / Zarar %": "{:+.2f}%", "Maks. Kâr %": "{:+.2f}%", "Maks. Düşüş %": "{:+.2f}%",
                        "Pozisyonda Gün": "{:.1f}", "Geçen Gün": "{:.0f}",
                    }, na_rep="-")
                    .map(performans_hucre_stili, subset=["Kâr / Zarar %"])
                    .set_properties(**{
                        "font-size": "13px",
                        "text-align": "left",
                        "white-space": "nowrap",
                    })
                    .set_properties(
                        subset=[c for c in ["İlk Alım Fiyatı", "Güncel Fiyat", "Kapanış Fiyatı", "Kâr / Zarar %", "Geçen Gün"] if c in df_gorunum.columns],
                        **{"text-align": "right", "font-variant-numeric": "tabular-nums"}
                    )
                    .set_table_styles([
                        {"selector": "th", "props": [("font-weight", "700"), ("text-align", "left"), ("white-space", "nowrap")]},
                        {"selector": "td", "props": [("border-bottom", "1px solid rgba(128,128,128,0.18)")]},
                    ])
                )

            st.markdown("### 📌 Aktif Alım Pozisyonları")
            if acik_df.empty:
                st.info("Şu anda açık alım pozisyonu bulunmuyor.")
            else:
                aktif_gorunum = pd.DataFrame({
                    "İlk Alım Tarihi": acik_df["_tarih"].dt.strftime("%d.%m.%Y %H:%M"),
                    "Varlık": acik_df.get("ticker"),
                    "İlk Sinyal": acik_df.get("ilk_sinyal").fillna("— Eski kayıt") if "ilk_sinyal" in acik_df.columns else pd.Series(["— Eski kayıt"] * len(acik_df)),
                    "Güncel Sinyal": acik_df.get("sinyal"),
                    "İlk Alım Fiyatı": acik_df.get("giris_fiyati"),
                    "Güncel Fiyat": acik_df.get("son_fiyat"),
                    "Kâr / Zarar %": acik_df.get("getiri_yuzde"),
                    "Geçen Gün": acik_gecen.reset_index(drop=True),
                    "Durum": "🟢 Açık",
                })
                st.dataframe(
                    tablo_stili(aktif_gorunum),
                    use_container_width=True,
                    height=min(440, 82 + 36 * len(aktif_gorunum)),
                    hide_index=True,
                )
                st.caption(
                    "Performans, hissenin bu alım dönemindeki ilk sinyal fiyatından güncel fiyata göre hesaplanır. "
                    "Aynı dönem içinde Kademeli Alım, Kusursuz Alım veya Kırılım arasında geçiş olması giriş fiyatını değiştirmez."
                )

            with st.expander(f"🗃️ Kapanmış Pozisyon Geçmişi ({len(kapali_df)})", expanded=False):
                if kapali_df.empty:
                    st.info("Henüz kapanmış alım dönemi bulunmuyor.")
                else:
                    # Kapanmış dönemin yalnızca çıkış getirisini değil,
                    # süreç içindeki kaliteyi de göster.
                    giris_fiyat_seri = pd.to_numeric(
                        kapali_df.get("giris_fiyati"), errors="coerce"
                    )
                    kapanis_fiyat_seri = pd.to_numeric(
                        kapali_df.get("kapanis_fiyati", kapali_df.get("son_fiyat")),
                        errors="coerce"
                    )
                    hesaplanan_getiri = (
                        (kapanis_fiyat_seri / giris_fiyat_seri) - 1.0
                    ) * 100.0
                    mevcut_getiri = pd.to_numeric(
                        kapali_df.get("getiri_yuzde"), errors="coerce"
                    )
                    kapanis_getiri = mevcut_getiri.where(
                        mevcut_getiri.notna(), hesaplanan_getiri
                    )

                    pozisyonda_gun = (
                        (kapali_df["_kapanis_tarih"] - kapali_df["_tarih"])
                        .dt.total_seconds() / 86400.0
                    ).clip(lower=0)

                    def _ufuk_extreme(row, tip="max"):
                        ufuklar = _guvenli_dict(row.get("performans_ufuklari"))
                        vals = []
                        if isinstance(ufuklar, dict):
                            for item in ufuklar.values():
                                try:
                                    g = float((item or {}).get("getiri"))
                                    if np.isfinite(g):
                                        vals.append(g)
                                except Exception:
                                    pass

                        direkt_alan = (
                            "max_yukselis_45g" if tip == "max"
                            else "max_dusus_45g"
                        )
                        try:
                            direkt = float(row.get(direkt_alan))
                            if np.isfinite(direkt):
                                return direkt
                        except Exception:
                            pass

                        if not vals:
                            return np.nan
                        return max(vals) if tip == "max" else min(vals)

                    def _hedef_gordu(row, hedef_no):
                        kayitli = row.get(f"ilk_tp{hedef_no}_gordu")
                        if isinstance(kayitli, (bool, np.bool_)):
                            return "✅" if bool(kayitli) else "❌"
                        try:
                            giris=float(row.get("giris_fiyati")); hedef=float(row.get(f"ilk_tp{hedef_no}"))
                        except Exception:
                            return "—"
                        if not np.isfinite(giris) or giris<=0 or not np.isfinite(hedef) or hedef<=0: return "—"
                        gorulen=_ufuk_extreme(row,"max")
                        if not np.isfinite(gorulen): return "—"
                        return "✅" if gorulen >= ((hedef/giris)-1)*100 else "❌"

                    max_kar = pd.to_numeric(
                        kapali_df.get("donem_max_kar", pd.Series(np.nan, index=kapali_df.index)), errors="coerce"
                    )
                    max_dusus = pd.to_numeric(
                        kapali_df.get("donem_max_dusus", pd.Series(np.nan, index=kapali_df.index)), errors="coerce"
                    )
                    eski_max = kapali_df.apply(lambda r: _ufuk_extreme(r, "max"), axis=1)
                    eski_min = kapali_df.apply(lambda r: _ufuk_extreme(r, "min"), axis=1)
                    max_kar = max_kar.where(max_kar.notna(), eski_max)
                    max_dusus = max_dusus.where(max_dusus.notna(), eski_min)

                    kapanmis_gorunum = pd.DataFrame({
                        "İlk Alım Tarihi": kapali_df["_tarih"].dt.strftime("%d.%m.%Y %H:%M"),
                        "Kapanış Tarihi": kapali_df["_kapanis_tarih"].dt.strftime("%d.%m.%Y %H:%M"),
                        "Varlık": kapali_df.get("ticker"),
                        "Son Alım Sinyali": kapali_df.get("sinyal"),
                        "Kapanış Nedeni": kapali_df.get("kapanis_sinyali"),
                        "İlk Alım Fiyatı": giris_fiyat_seri,
                        "Kapanış Fiyatı": kapanis_fiyat_seri,
                        "Kâr / Zarar %": kapanis_getiri,
                        "Pozisyonda Gün": pozisyonda_gun.round(1),
                        "Maks. Kâr %": max_kar,
                        "Maks. Düşüş %": max_dusus,
                        "İlk Stop": pd.to_numeric(kapali_df.get("ilk_stop", pd.Series(np.nan, index=kapali_df.index)), errors="coerce"),
                        "İlk TP1": pd.to_numeric(kapali_df.get("ilk_tp1", pd.Series(np.nan, index=kapali_df.index)), errors="coerce"),
                        "İlk TP2": pd.to_numeric(kapali_df.get("ilk_tp2", pd.Series(np.nan, index=kapali_df.index)), errors="coerce"),
                        "İlk TP3": pd.to_numeric(kapali_df.get("ilk_tp3", pd.Series(np.nan, index=kapali_df.index)), errors="coerce"),
                        "TP1": kapali_df.apply(lambda r: _hedef_gordu(r, 1), axis=1),
                        "TP2": kapali_df.apply(lambda r: _hedef_gordu(r, 2), axis=1),
                        "TP3": kapali_df.apply(lambda r: _hedef_gordu(r, 3), axis=1),
                        "Stop": kapali_df.apply(lambda r: ("✅" if bool(r.get("ilk_stop_gordu")) else "❌") if isinstance(r.get("ilk_stop_gordu"), (bool, np.bool_)) else "—", axis=1),
                        "Durum": "⚪ Kapalı",
                    })
                    # v1.7.27 — Kapanmış geçmişi Streamlit'in beyaz grid temasından bağımsız
                    # özel IZFIN tablosu olarak göster.
                    _kg = kapanmis_gorunum.copy()

                    # Kapanmış dönem özetleri.
                    _ret = pd.to_numeric(_kg["Kâr / Zarar %"], errors="coerce")
                    _days = pd.to_numeric(_kg["Pozisyonda Gün"], errors="coerce")
                    _valid_ret = _ret.dropna()
                    _win_rate = float((_valid_ret > 0).mean() * 100) if not _valid_ret.empty else np.nan
                    _avg_ret = float(_valid_ret.mean()) if not _valid_ret.empty else np.nan
                    _med_days = float(_days.dropna().median()) if not _days.dropna().empty else np.nan

                    # Daha zengin kapanmış dönem istatistikleri.
                    _unique_tickers = int(_kg["Varlık"].nunique()) if "Varlık" in _kg.columns else 0

                    _tp1_rate = np.nan
                    if "TP1" in _kg.columns:
                        _tp1_vals = _kg["TP1"].astype(str).str.upper()
                        _tp1_rate = float(_tp1_vals.isin(["EVET", "TRUE", "1", "✓"]).mean() * 100)

                    _stop_rate = np.nan
                    if "Stop" in _kg.columns:
                        _stop_vals = _kg["Stop"].astype(str).str.upper()
                        _stop_rate = float(_stop_vals.isin(["EVET", "TRUE", "1", "✓"]).mean() * 100)

                    _best_txt = "—"
                    _worst_txt = "—"
                    if not _valid_ret.empty:
                        try:
                            _best_i = _ret.idxmax()
                            _worst_i = _ret.idxmin()
                            _best_txt = f"{_kg.loc[_best_i, 'Varlık']} %{float(_ret.loc[_best_i]):+.1f}"
                            _worst_txt = f"{_kg.loc[_worst_i, 'Varlık']} %{float(_ret.loc[_worst_i]):+.1f}"
                        except Exception:
                            pass

                    _median_ret = float(_valid_ret.median()) if not _valid_ret.empty else np.nan

                    st.markdown(
                        f"""
                        <div class="iz-closed-kpis iz-closed-kpis-wide">
                            <div><small>KAPANMIŞ ALIM DÖNEMİ</small><b>{len(_kg)}</b></div>
                            <div><small>FARKLI HİSSE</small><b>{_unique_tickers}</b></div>
                            <div><small>POZİTİF KAPANIŞ</small><b>{f"%{_win_rate:.1f}" if np.isfinite(_win_rate) else "—"}</b></div>
                            <div><small>ORT. GETİRİ</small><b class="{'pos' if np.isfinite(_avg_ret) and _avg_ret >= 0 else 'neg'}">{f"%{_avg_ret:+.2f}" if np.isfinite(_avg_ret) else "—"}</b></div>
                            <div><small>MEDYAN GETİRİ</small><b class="{'pos' if np.isfinite(_median_ret) and _median_ret >= 0 else 'neg'}">{f"%{_median_ret:+.2f}" if np.isfinite(_median_ret) else "—"}</b></div>
                            <div><small>MEDYAN SÜRE</small><b>{f"{_med_days:.1f} gün" if np.isfinite(_med_days) else "—"}</b></div>
                            <div><small>TP1 GÖRÜLME</small><b>{f"%{_tp1_rate:.1f}" if np.isfinite(_tp1_rate) else "—"}</b></div>
                            <div><small>STOP GÖRÜLME</small><b>{f"%{_stop_rate:.1f}" if np.isfinite(_stop_rate) else "—"}</b></div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    # Kullanıcıya ham tablodan önce kısa ve anlaşılır sistem yorumu.
                    _yorum_parcalari = []

                    if np.isfinite(_win_rate):
                        if _win_rate >= 65:
                            _yorum_parcalari.append(f"Kapanmış alım dönemlerinin %{_win_rate:.0f}'i pozitif sonuçlanmış; geçmiş sinyal seçimi güçlü görünüyor.")
                        elif _win_rate >= 50:
                            _yorum_parcalari.append(f"Kapanmış alım dönemlerinin %{_win_rate:.0f}'i pozitif; sistem geçmişte hafif pozitif bir seçicilik göstermiş.")
                        else:
                            _yorum_parcalari.append(f"Pozitif kapanış oranı %{_win_rate:.0f}; geçmiş sinyal seçimi daha seçici filtrelere ihtiyaç duyabilir.")

                    if np.isfinite(_avg_ret) and np.isfinite(_median_ret):
                        if _avg_ret > _median_ret + 2:
                            _yorum_parcalari.append("Ortalama getiri medyanın belirgin üzerinde; birkaç güçlü kazanan toplam performansı yukarı taşıyor.")
                        elif _median_ret > _avg_ret + 2:
                            _yorum_parcalari.append("Medyan getiri ortalamanın üzerinde; birkaç zayıf dönem genel ortalamayı aşağı çekiyor.")
                        elif _avg_ret > 0:
                            _yorum_parcalari.append("Ortalama ve medyan getiri birbirine yakın; sonuç dağılımı görece dengeli.")
                        else:
                            _yorum_parcalari.append("Ortalama ve medyan getirinin birlikte zayıf olması, kapanış disiplininin ayrıca incelenmesini gerektiriyor.")

                    if np.isfinite(_tp1_rate) and np.isfinite(_stop_rate):
                        if _tp1_rate > _stop_rate + 10:
                            _yorum_parcalari.append("TP1 görülme oranı stop görülme oranından belirgin yüksek; giriş sonrası olumlu hareket üretme kapasitesi iyi.")
                        elif _stop_rate > _tp1_rate + 10:
                            _yorum_parcalari.append("Stop görülme oranı TP1 oranından yüksek; giriş zamanlaması veya risk filtresi geliştirilebilir.")
                        else:
                            _yorum_parcalari.append("TP1 ve stop görülme oranları birbirine yakın; sinyal sonrası yön ayrışması sınırlı.")

                    if _unique_tickers <= 3 and len(_kg) >= 5:
                        _yorum_parcalari.append("Sonuçların önemli bölümü az sayıda hissede yoğunlaşmış; genelleme yaparken örneklem çeşitliliğine dikkat edilmeli.")

                    _yorum_html = "".join(
                        f"<li>{html.escape(str(x))}</li>"
                        for x in _yorum_parcalari[:4]
                    ) or "<li>Yeterli kapanmış dönem biriktikçe sistem yorumu burada daha anlamlı hale gelecek.</li>"

                    st.markdown(
                        f"""
                        <div class="iz-closed-insight-card">
                            <div class="iz-closed-insight-head">
                                <div>
                                    <small>IZFIN GEÇMİŞ PERFORMANS ÖZETİ</small>
                                    <h4>Sistem geçmişte ne yaptı?</h4>
                                </div>
                                <div class="iz-closed-extremes">
                                    <span><b>En iyi</b> {_best_txt}</span>
                                    <span><b>En zayıf</b> {_worst_txt}</span>
                                </div>
                            </div>
                            <ul>{_yorum_html}</ul>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    def _fmt_num(v, suffix="", signed=False):
                        try:
                            x = float(v)
                            if not np.isfinite(x):
                                return "—"
                            return f"{x:+.2f}{suffix}" if signed else f"{x:.2f}{suffix}"
                        except Exception:
                            return "—"

                    _rows = []
                    for _, _r in _kg.iterrows():
                        _ret_v = pd.to_numeric(pd.Series([_r.get("Kâr / Zarar %")]), errors="coerce").iloc[0]
                        _ret_cls = "pos" if pd.notna(_ret_v) and _ret_v > 0 else ("neg" if pd.notna(_ret_v) and _ret_v < 0 else "neu")
                        _ticker = html.escape(str(_r.get("Varlık", "—")))
                        _reason = html.escape(str(_r.get("Kapanış Nedeni", "—")))
                        _signal = html.escape(str(_r.get("Son Alım Sinyali", "—")))
                        _rows.append(
                            "<tr>"
                            f"<td class='date'>{html.escape(str(_r.get('İlk Alım Tarihi','—')))}</td>"
                            f"<td class='date'>{html.escape(str(_r.get('Kapanış Tarihi','—')))}</td>"
                            f"<td><span class='iz-ticker-chip'>{_ticker}</span></td>"
                            f"<td><span class='iz-signal-chip'>{_signal}</span></td>"
                            f"<td><span class='iz-close-reason'>{_reason}</span></td>"
                            f"<td class='num'>{_fmt_num(_r.get('İlk Alım Fiyatı'))}</td>"
                            f"<td class='num'>{_fmt_num(_r.get('Kapanış Fiyatı'))}</td>"
                            f"<td class='num { _ret_cls }'>{_fmt_num(_r.get('Kâr / Zarar %'), '%', True)}</td>"
                            f"<td class='num'>{_fmt_num(_r.get('Pozisyonda Gün'))}</td>"
                            f"<td class='num pos-soft'>{_fmt_num(_r.get('Maks. Kâr %'), '%', True)}</td>"
                            f"<td class='num neg-soft'>{_fmt_num(_r.get('Maks. Düşüş %'), '%', True)}</td>"
                            f"<td class='num'>{_fmt_num(_r.get('İlk Stop'))}</td>"
                            f"<td class='num'>{_fmt_num(_r.get('İlk TP1'))}</td>"
                            f"<td class='center'>{html.escape(str(_r.get('TP1','—')))}</td>"
                            f"<td class='center'>{html.escape(str(_r.get('TP2','—')))}</td>"
                            f"<td class='center'>{html.escape(str(_r.get('TP3','—')))}</td>"
                            f"<td class='center'>{html.escape(str(_r.get('Stop','—')))}</td>"
                            "</tr>"
                        )

                    _closed_html = (
                        "<div class='iz-closed-table-shell'>"
                        "<div class='iz-closed-table-scroll'>"
                        "<table class='iz-closed-table'>"
                        "<thead><tr>"
                        "<th>İlk Alım</th><th>Kapanış</th><th>Varlık</th><th>Son Sinyal</th><th>Kapanış Nedeni</th>"
                        "<th>Giriş</th><th>Kapanış</th><th>K/Z %</th><th>Gün</th><th>Maks. Kâr</th><th>Maks. Düşüş</th>"
                        "<th>İlk Stop</th><th>İlk TP1</th><th>TP1</th><th>TP2</th><th>TP3</th><th>Stop</th>"
                        "</tr></thead><tbody>"
                        + "".join(_rows)
                        + "</tbody></table></div></div>"
                    )
                    st.markdown(_closed_html, unsafe_allow_html=True)

                    # Kapanış nedenleri dağılımı — kullanıcıya sistemin neden pozisyon kapattığını gösterir.
                    if "Kapanış Nedeni" in _kg.columns:
                        try:
                            _reason_counts = _kg["Kapanış Nedeni"].fillna("Belirsiz").astype(str).value_counts().head(5)
                            _reason_chips = "".join(
                                f"<span><b>{html.escape(str(k))}</b> {int(v)}</span>"
                                for k, v in _reason_counts.items()
                            )
                            st.markdown(
                                f"""
                                <div class="iz-close-reason-summary">
                                    <small>EN SIK KAPANIŞ NEDENLERİ</small>
                                    <div>{_reason_chips}</div>
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )
                        except Exception:
                            pass

                    st.caption(
                        "Aynı hissede alım sinyali sona erip daha sonra yeniden oluşursa yeni dönem aktif tabloda açılır; "
                        "önceki dönem burada saklanır. Maksimum kâr/düşüş ve TP sütunları, ilgili alım dönemi için "
                        "yeterli karne/hedef verisi varsa gösterilir. Yeni kayıtlarda maksimum kâr/düşüş ve hedef hitleri yalnızca pozisyonun açık kaldığı dönemden hesaplanır. "
                        "Aynı günlük mum içinde hem stop hem hedef görülmüşse gün içi gerçekleşme sırası bu günlük ölçümden belirlenemez. Önceki sürümlerde eksik ölçümler '—' olarak gösterilir."
                    )


            st.markdown("---")
            st.markdown("### 🏆 IZFIN Performans Karnesi")
            st.caption(
                "Yeni sinyaller güncel IZFIN strateji sürümüyle dondurulur. 1/5/10/20/45 işlem günü "
                "sonuçları sonradan değiştirilmez; ABD hisseleri NASDAQ, BIST hisseleri BIST100 ile karşılaştırılır."
            )

            kc1, kc2 = st.columns([1, 3])
            with kc1:
                karne_guncelle = st.button("🏆 Karneleri Güncelle", use_container_width=True)
            with kc2:
                ufuk_secimi = st.selectbox(
                    "Karne ufku (işlem günü)",
                    options=[1, 5, 10, 20, 45],
                    index=3,
                    key="izfin_karne_ufku",
                )

            if karne_guncelle:
                with st.spinner("IZFIN performans karnesi güncelleniyor..."):
                    kayitlar = performans_karnelerini_guncelle(kayitlar)
                st.success("Karne güncellendi. Yeterli işlem günü oluşan sinyaller donduruldu.")

            karne_df = performans_karnesi_ozeti(kayitlar, gun=int(ufuk_secimi))
            if karne_df.empty:
                st.info(
                    f"Henüz +{ufuk_secimi} işlem günü tamamlamış ölçülebilir sinyal yok. "
                    "Yeni IZFIN sinyalleri biriktikçe bu bölüm otomatik anlam kazanacak."
                )
            else:
                pozitif_oran = float((karne_df["getiri"] > 0).mean() * 100)
                medyan_getiri = float(karne_df["getiri"].median())
                alfa_seri = pd.to_numeric(karne_df["alfa"], errors="coerce").dropna()
                benchmark_ustu = float((alfa_seri > 0).mean() * 100) if not alfa_seri.empty else np.nan
                medyan_alfa = float(alfa_seri.median()) if not alfa_seri.empty else np.nan

                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Ölçülen Sinyal", len(karne_df))
                c2.metric("Pozitif Sonuç", f"%{pozitif_oran:.1f}")
                c3.metric(f"+{ufuk_secimi}G Medyan", f"%{medyan_getiri:+.2f}")
                c4.metric(
                    "Benchmark Üstü",
                    f"%{benchmark_ustu:.1f}" if np.isfinite(benchmark_ustu) else "—"
                )

                if np.isfinite(medyan_alfa):
                    st.caption(f"Medyan göreceli performans (alfa): %{medyan_alfa:+.2f}")

                # Ana karne olay değil varlık bazında gösterilir. Böylece aynı hissedeki
                # farklı gerçek sinyal dönemleri kopya satır gibi görünmez; eksik eski
                # eksik geçmiş metadata da kullanıcıya ham değer olarak yansımaz.
                detay_karne = karne_df.copy()
                detay_karne["getiri"] = pd.to_numeric(detay_karne["getiri"], errors="coerce")
                detay_karne["alfa"] = pd.to_numeric(detay_karne["alfa"], errors="coerce")

                gorunum = (
                    detay_karne.groupby("ticker", dropna=False)
                    .agg(
                        **{
                            "Sinyal Sayısı": ("getiri", "size"),
                            "Başarı Oranı %": ("getiri", lambda x: float((x > 0).mean() * 100)),
                            f"+{ufuk_secimi}G Medyan Getiri %": ("getiri", "median"),
                            "Medyan Benchmark Farkı %": ("alfa", "median"),
                        }
                    )
                    .reset_index()
                    .rename(columns={"ticker": "Varlık"})
                    .sort_values(f"+{ufuk_secimi}G Medyan Getiri %", ascending=False)
                )

                st.dataframe(
                    gorunum.style.format({
                        "Sinyal Sayısı": "{:.0f}",
                        "Başarı Oranı %": "{:.1f}%",
                        f"+{ufuk_secimi}G Medyan Getiri %": "{:+.2f}%",
                        "Medyan Benchmark Farkı %": "{:+.2f}%",
                    }, na_rep="—"),
                    use_container_width=True,
                    hide_index=True,
                )

                with st.expander("Ölçüm dönemlerini göster", expanded=False):
                    detay = detay_karne.copy()
                    detay["sinyal_tarihi"] = pd.to_datetime(
                        detay["sinyal_tarihi"], errors="coerce"
                    ).dt.strftime("%d.%m.%Y")
                    detay = detay.rename(columns={
                        "ticker": "Varlık",
                        "sinyal_tarihi": "Sinyal Tarihi",
                        "sinyal": "Sinyal",
                        "getiri": f"+{ufuk_secimi}G Getiri %",
                        "alfa": "Benchmark Farkı %",
                    })
                    detay_kolonlari = [
                        "Varlık", "Sinyal Tarihi", "Sinyal",
                        f"+{ufuk_secimi}G Getiri %", "Benchmark Farkı %"
                    ]
                    # Tamamı eksik olan tarih/sinyal alanlarını boş sütun olarak gösterme.
                    detay_kolonlari = [
                        c for c in detay_kolonlari
                        if c in detay.columns and not detay[c].isna().all()
                    ]
                    st.dataframe(
                        detay[detay_kolonlari].sort_values(
                            f"+{ufuk_secimi}G Getiri %", ascending=False
                        ).style.format({
                            f"+{ufuk_secimi}G Getiri %": "{:+.2f}%",
                            "Benchmark Farkı %": "{:+.2f}%",
                        }, na_rep="—"),
                        use_container_width=True,
                        hide_index=True,
                    )

                if len(karne_df) < 30:
                    st.warning(
                        "Örneklem henüz küçük. Başarı oranlarını karar vermek için kullanmadan önce "
                        "en az 30, tercihen 100+ bağımsız sinyal biriktirmek daha sağlıklıdır."
                    )


if aktif_sayfa == "🧪 Strateji Laboratuvarı":
    st.subheader("🧪 Strateji Laboratuvarı · IZFIN Daily Core Backtest")
    st.markdown(
        "Geçmişte her gün için yalnızca o güne kadar bilinen verilerle **IZFIN günlük çekirdek karar motorunu** yeniden çalıştırır. "
        "Merkezi motor yalnızca GÜÇLÜ AL / AL / ERKEN AL dediğinde test işlemi açılır; ardından 5/10/20/45 günlük hareket ve Stop/TP sonucu ölçülür. "
        "Uzun dönem intraday geçmişi olmadığı için 5dk/15dk/1s giriş motoru uydurulmaz; Daily MTF ve Giriş Proxy açıkça ayrı gösterilir."
    )

    bt_c1, bt_c2 = st.columns([2, 1])
    with bt_c1:
        # Uzun listelerde klasik selectbox yerine arama odaklı seçim kullanılır.
        # Kullanıcı kayıtlı havuzda olmayan geçerli bir Yahoo sembolünü de doğrudan test edebilir.
        bt_havuz = sorted(set(str(x).strip().upper() for x in tum_varliklar_havuzu if str(x).strip()))
        bt_arama = st.text_input(
            "Test edilecek varlığı ara",
            value=st.session_state.get("bt_son_ticker", ""),
            placeholder="Örn. NVDA, AAPL, THYAO.IS",
            key="bt_ticker_arama",
            help="Sembolü yazın. Kayıtlı varlıklarda eşleşmeler daraltılır; listede olmayan geçerli Yahoo sembolleri de test edilebilir.",
        ).strip().upper()

        bt_ticker = ""
        if bt_arama:
            # Önce sembolün başından eşleşenleri, sonra içinde geçenleri getir.
            baslayanlar = [x for x in bt_havuz if x.startswith(bt_arama)]
            icerenler = [x for x in bt_havuz if bt_arama in x and x not in baslayanlar]
            bt_eslesmeler = (baslayanlar + icerenler)[:25]

            if bt_arama in bt_havuz:
                bt_ticker = bt_arama
                st.caption(f"✅ Seçilen varlık: {bt_ticker}")
            elif bt_eslesmeler:
                bt_ticker = st.selectbox(
                    "Eşleşen varlıklar",
                    options=bt_eslesmeler,
                    key="bt_ticker_eslesme",
                    help="Aramayı daraltmak için sembolden daha fazla karakter yazabilirsiniz.",
                )
            else:
                bt_ticker = bt_arama
                st.caption(f"🔎 {bt_ticker} kayıtlı havuzda yok; geçerli bir Yahoo sembolüyse doğrudan test edilecek.")
        else:
            st.caption("Bir sembol yazın; örneğin NVDA veya THYAO.IS.")

    with bt_c2:
        bt_period = st.selectbox("Geçmiş dönem", ["3y", "5y", "10y"], index=1, key="bt_period")

    bt_calistir = st.button(
        "🧪 Backtest'i Çalıştır",
        type="primary",
        use_container_width=True,
        disabled=not bool(bt_ticker),
    )

    if bt_calistir:
        st.session_state.bt_son_ticker = bt_ticker
        with st.spinner("Geçmiş IZFIN Daily Core kararları yeniden hesaplanıyor..."):
            bt, stats = basit_backtest(bt_ticker, bt_period)

        if bt.empty:
            st.warning("Seçilen dönem için yeterli veri veya alım sinyali bulunamadı.")
        else:
            q1, q2, q3, q4 = st.columns(4)
            q1.metric("Bağımsız Test İşlemi", f"{int(stats['sinyal'])}")
            q2.metric("İşlem Başarı Oranı", f"%{stats['islem_basarisi']:.1f}")
            q3.metric("Ort. İşlem Sonucu", f"%{stats['islem_ort']:+.2f}")
            q4.metric("TP1 / Stop", f"%{stats['tp1_oran']:.1f} / %{stats['stop_oran']:.1f}")

            s1, s2, s3, s4 = st.columns(4)
            s1.metric("20G Kârda", f"%{stats['kazanma20']:.1f}")
            s2.metric("20G Ort.", f"%{stats['ort20']:+.2f}")
            s3.metric("45G Kârda", f"%{stats['kazanma45']:.1f}")
            s4.metric("45G Ort.", f"%{stats['ort45']:+.2f}")

            if stats.get("belirsiz", 0):
                st.caption(
                    f"ℹ️ {stats['belirsiz']} örnekte aynı günlük mum içinde hem Stop hem TP1 görüldü. "
                    "Günlük veri sıralamayı göstermediği için muhafazakâr biçimde Stop önce kabul edildi."
                )

            st.markdown("### 📌 Merkezi karar türlerine göre özet")
            ozet = (
                bt.groupby("Sinyal")
                .agg(
                    Örnek=("Sinyal", "size"),
                    **{
                        "İşlem Başarı %": ("İşlem Sonucu %", lambda x: (x > 0).mean() * 100),
                        "Ort. İşlem %": ("İşlem Sonucu %", "mean"),
                        "TP1 İlk %": ("İlk Olay", lambda x: (x == "TP1").mean() * 100),
                        "Stop İlk %": ("İlk Olay", lambda x: x.astype(str).str.startswith("STOP").mean() * 100),
                        "20G Kârda %": ("20G %", lambda x: (x > 0).mean() * 100),
                        "20G Ort. %": ("20G %", "mean"),
                        "45G Kârda %": ("45G %", lambda x: (x > 0).mean() * 100),
                        "45G Ort. %": ("45G %", "mean"),
                    },
                )
                .reset_index()
                .sort_values(["İşlem Başarı %", "Örnek"], ascending=False)
            )
            ozet_stil = ozet.style.format({
                "Örnek": "{:.0f}",
                "İşlem Başarı %": "{:.1f}%",
                "Ort. İşlem %": "{:+.2f}%",
                "TP1 İlk %": "{:.1f}%",
                "Stop İlk %": "{:.1f}%",
                "20G Kârda %": "{:.1f}%",
                "20G Ort. %": "{:+.2f}%",
                "45G Kârda %": "{:.1f}%",
                "45G Ort. %": "{:+.2f}%",
            }, na_rep="-")
            st.dataframe(ozet_stil, use_container_width=True, hide_index=True)

            with st.expander("🔬 Geçmiş IZFIN kararlarını incele", expanded=False):
                detay_kolonlar = [
                    "Tarih", "Sinyal", "Teknik Profil", "Ön Sinyal",
                    "Hibrit Skor", "Güven %", "Daily MTF %", "Giriş Proxy",
                    "Giriş", "İlk Stop", "İlk TP1", "İlk Olay", "İşlem Sonucu %",
                    "20G %", "45G %",
                ]
                detay_bt = bt[[k for k in detay_kolonlar if k in bt.columns]].copy()
                for tarih_col in ["Tarih"]:
                    if tarih_col in detay_bt:
                        detay_bt[tarih_col] = pd.to_datetime(detay_bt[tarih_col], errors="coerce").dt.strftime("%Y-%m-%d")
                st.dataframe(
                    detay_bt.style.format({
                        "Hibrit Skor": "{:.0f}", "Güven %": "{:.0f}", "Daily MTF %": "{:.0f}",
                        "Giriş Proxy": "{:.0f}", "Giriş": "{:.2f}", "İlk Stop": "{:.2f}", "İlk TP1": "{:.2f}",
                        "İşlem Sonucu %": "{:+.2f}%", "20G %": "{:+.2f}%", "45G %": "{:+.2f}%",
                    }, na_rep="-"),
                    use_container_width=True, hide_index=True,
                    height=min(520, 82 + 35 * len(detay_bt)),
                )
                st.caption("Bu tablo, geçmişte hangi tarihte hangi merkezi IZFIN kararının işlem açtığını ve karar anındaki günlük çekirdek puanlarını gösterir.")

            with st.expander("ℹ️ Backtest sonuçları nasıl okunur?", expanded=False):
                st.markdown("""
- **Bu test artık eski basit dört koşulu değil, IZFIN'in günlük çekirdek analiz zincirini geçmişte yeniden çalıştırır.** Hibrit skor, ADX/DI, CMF, SuperTrend, risk, teknik profil, güven ve merkezi karar birlikte değerlendirilir.
- **Yalnızca merkezi motorun GÜÇLÜ AL / AL / ERKEN AL aksiyonları işlem açar.** TEYİT BEKLE ve İZLE geçmiş işlem sayılmaz.
- **Daily MTF % ve Giriş Proxy**, 5–10 yıllık intraday geçmiş bulunmadığı için günlük veriden türetilen doğrulama alanlarıdır; canlı 5dk/15dk/1s Giriş Motoruymuş gibi sunulmaz.
- **20G / 45G sonuçları**, çıkıştan bağımsız sabit ufuk ölçümüdür; hissenin karar sonrası yön seçme kalitesini gösterir.
- İlk Stop ve TP1 yalnızca sinyal gününe kadar bilinen verilerle hesaplanıp dondurulur. Aynı gün ikisi de görülürse test muhafazakâr biçimde Stop'u önce kabul eder.
- Komisyon, vergi, spread ve gerçek emir kayması modellenmez; sonuçlar gerçek işlem getirisi garantisi değildir.
""")
