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
        background-image: url('https://upload.wikimedia.org/wikipedia/commons/e/e3/Auvere_Power_Plant%2C_2013..jpg');
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

@st.cache_data(ttl=300) # Uuenda iga 5 min tagant
def get_auvere_data():
    client = EntsoePandasClient(api_key=API_KEY)
    
    # 1. Ajad paika (Võtame ainult viimased 24h)
    end = pd.Timestamp.now(tz='Europe/Tallinn')
    start = end - timedelta(hours=24) 
    
    try:
        # Pärime ainult 1 päeva andmed (väga kiire)
        df = client.query_generation_per_plant('EE', start=start, end=end)
        
        # Leiame Auvere veeru
        auvere_col = [c for c in df.columns if 'Auvere' in str(c)]
        if not auvere_col:
            return None, "Andmed puuduvad (veerg kadunud)"
            
        data = df[auvere_col[0]]
        
        # Võtame kõige viimase teadaoleva numbri
        current_mw = data.iloc[-1]
        
        # --- STATISTIKA FEIKIMINE ---
        # Kuna me ei tõmba enam aasta andmeid, siis me ei saa 
        # arvutada tegelikku "päevi maas" statsi.
        # Paneme siia hetkel placeholderid, et kood katki ei läheks.
        
        return {
            "current_mw": round(current_mw, 1),
            "is_running": current_mw > 15, # Lävepakuks 15MW
            "days_down": "---",  # Statistikat praegu ei arvuta
            "uptime": "---"      # Statistikat praegu ei arvuta
        }, None
        
    except Exception as e:
        return None, str(e)

@st.cache_data(ttl=7200) # Uudiseid uuenda iga 2h tagant
def get_news():
    # Kasutame Google News RSS-i, mis otsib märksõna "Auvere elektrijaam"
    # hl=et (keel), gl=EE (regioon)
    url = "https://news.google.com/rss/search?q=auvere+elektrijaam&hl=et&gl=EE&ceid=EE:et"
    
    try:
        # 1. Teeme päringu
        response = requests.get(url, timeout=5)
        
        # 2. Parsime XML sisu
        soup = BeautifulSoup(response.content, features='xml')
        
        # 3. Võtame esimesed 5 uudist
        items = soup.findAll('item')[:5]
        
        news_list = []
        for item in items:
            title = item.title.text
            link = item.link.text
            # Kuupäev on tavaliselt formaadis "Thu, 12 Feb 2026...", teeme ilusamaks
            pub_date = item.pubDate.text[:16] 
            
            news_list.append({
                "title": title,
                "link": link,
                "date": pub_date
            })
            
        return news_list

    except Exception as e:
        # Prindime vea konsooli, et näha mis juhtus
        print(f"Uudiste viga: {e}")
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
