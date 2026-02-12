import streamlit as st
import pandas as pd
from entsoe import EntsoePandasClient
import requests
from bs4 import BeautifulSoup
from datetime import timedelta
import os

# --- KONFIGURATSIOON ---
# See rida proovib võtta võtit Renderi keskkonnamuutujatest (os.environ)
# Kui sealt ei leia, proovib st.secrets (juhuks kui testid lokaalselt)
API_KEY = os.environ.get("ENTSOE_KEY")

if not API_KEY:
    try:
        API_KEY = st.secrets["ENTSOE_KEY"]
    except:
        st.error("API võti on puudu! Palun lisa Renderisse Environment Variable 'ENTSOE_KEY'.")
        st.stop()
st.set_page_config(page_title="Auvere Fännileht", page_icon="⚡", layout="centered")

# --- CSS STILISTIKA (Silvia Ilves / Glamuur) ---
st.markdown("""
    <style>
    /* Taust */
    .stApp {
        background-image: url('https://upload.wikimedia.org/wikipedia/commons/thumb/5/5e/Auvere_elektrijaam_2015.jpg/1200px-Auvere_elektrijaam_2015.jpg');
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
    }
    
    /* Tume kiht tausta peal */
    .stApp::before {
        content: "";
        position: absolute;
        top: 0; left: 0; width: 100%; height: 100%;
        background: rgba(0, 0, 0, 0.75);
        z-index: -1;
    }

    /* Pealkirjad ja tekstid */
    h1, h2, h3, p, div { color: white !important; font-family: 'Helvetica Neue', sans-serif; }
    h1 { 
        text-transform: uppercase; 
        color: gold !important; 
        text-shadow: 0 0 10px rgba(255, 215, 0, 0.5);
        text-align: center;
        font-size: 3rem;
    }

    /* Staatuskast */
    .status-box {
        border: 2px solid gold;
        background: rgba(0,0,0,0.6);
        padding: 20px;
        border-radius: 15px;
        text-align: center;
        box-shadow: 0 0 30px rgba(255, 215, 0, 0.2);
        margin-bottom: 20px;
    }
    
    .big-status { font-size: 4rem; font-weight: bold; margin: 10px 0; }
    .producing { color: #2ecc71 !important; text-shadow: 0 0 20px #2ecc71; }
    .offline { color: #e74c3c !important; text-shadow: 0 0 20px #e74c3c; }

    /* Pildiraam */
    .star-image {
        display: block;
        margin-left: auto;
        margin-right: auto;
        width: 150px;
        height: 150px;
        border-radius: 50%;
        border: 4px solid gold;
        object-fit: cover;
        margin-bottom: 20px;
    }
    </style>
""", unsafe_allow_html=True)

# --- FUNKTSIOONID ---

@st.cache_data(ttl=3600) # Hoiab andmeid vahemälus 1h, et API-t mitte spämmida
def get_auvere_data():
    client = EntsoePandasClient(api_key=API_KEY)
    end = pd.Timestamp.now(tz='Europe/Tallinn')
    start = end - timedelta(days=365) # Võtame aasta andmed statistika jaoks
    
    try:
        # Pärime andmed
        df = client.query_generation_per_plant('EE', start=start, end=end)
        
        # Leiame õige veeru (nimi võib muutuda, otsime 'Auvere' järgi)
        auvere_col = [c for c in df.columns if 'Auvere' in str(c)]
        if not auvere_col:
            return None, "Andmed puuduvad"
            
        data = df[auvere_col[0]]
        current_mw = data.iloc[-1]
        
        # Statistika
        daily_max = data.resample('D').max()
        days_down = daily_max[daily_max < 10].count() # Alla 10MW loeme maas olevaks
        uptime = 100 - (days_down / daily_max.count() * 100)
        
        return {
            "current_mw": round(current_mw, 1),
            "is_running": current_mw > 10,
            "days_down": int(days_down),
            "uptime": round(uptime, 1)
        }, None
    except Exception as e:
        return None, str(e)

@st.cache_data(ttl=7200) # Uudiseid uuenda iga 2h tagant
def get_news():
    url = "https://otsing.err.ee/otsing?phrase=auvere"
    try:
        r = requests.get(url)
        soup = BeautifulSoup(r.content, 'html.parser')
        results = soup.select('.search-results__item')[:3]
        news = []
        for item in results:
            title = item.select_one('h3 a').text.strip()
            link = item.select_one('h3 a')['href']
            date = item.select_one('.search-results__time').text.strip()
            news.append({"title": title, "link": link, "date": date})
        return news
    except:
        return []

# --- LEHE SISU ---

# Pilt (URL otse HTML-i injectitud, aga võib ka st.image kasutada)
st.markdown('<img src="https://g.delfi.ee/images/pix/900x585/tN-1lW2kKk4/auvere-elektrijaam-92047321.jpg" class="star-image">', unsafe_allow_html=True)

st.title("AUVERE")
st.caption("Eesti energeetika *bad boy* fännileht")

data, error = get_auvere_data()

if error:
    st.error(f"Ühendus staariga katkes: {error}")
elif data:
    # STAATUS
    status_text = "LAVAL (TÖÖTAB)" if data['is_running'] else "PUHKAB (MAAS)"
    status_class = "producing" if data['is_running'] else "offline"
    
    st.markdown(f"""
        <div class="status-box">
            <div style="font-size: 1.2rem; color: #ccc;">Hetkeseis:</div>
            <div class="big-status {status_class}">{status_text}</div>
            <div style="font-size: 2rem; color: white;">{data['current_mw']} MW</div>
        </div>
    """, unsafe_allow_html=True)

    # STATISTIKA VEERUD
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Päevi maas (viimane aasta)", f"{data['days_down']} päeva")
    with col2:
        st.metric("Töökindlus", f"{data['uptime']}%")

    st.markdown("---")

# UUDISED
st.subheader("Viimased draamad meedias")
news = get_news()
if news:
    for n in news:
        st.markdown(f"**{n['date']}** - [{n['title']}]({n['link']})")
else:
    st.write("Draamat hetkel pole.")
