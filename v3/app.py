# bootstrap
from pathlib import Path
import sys
def _add_paths():
    here = Path(__file__).resolve()
    root = here.parent
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    for sub in ("core", "services"):
        ep = root / sub
        if ep.exists() and str(ep) not in sys.path:
            sys.path.insert(0, str(ep))
_add_paths()
# -----

import streamlit as st
from streamlit.components.v1 import html

st.set_page_config(page_title="Stocks", layout="wide")

st.sidebar.success("Навигация: выбери страницу слева →")
with st.sidebar.expander("Доп. страницы", expanded=False):
	try:
		st.page_link("pages/0_🧰_Debug.py", label="Debug")
		st.page_link("pages/3_📥_Data_Load.py", label="Data Load")
		st.page_link("pages/5_🛒_Orders.py", label="Orders")
	except Exception:
		pass

st.write("Открой страницу слева: Dashboard, Analyzer, Auto Update, Settings. Доп. страницы в экспандере.")

# Hide specific default sidebar entries (Debug, Data Load, Orders)
try:
	js = """
	<script>
	const hideLabels = ["🧰", "📥", "🛒"];
	function hide() {
	  const sb = parent.document.querySelector("section[data-testid='stSidebar']");
	  if (!sb) { setTimeout(hide, 200); return; }
	  const links = sb.querySelectorAll("a");
	  links.forEach(a => {
	    const t = (a.textContent || "");
	    if (hideLabels.some(lbl => t.includes(lbl))) {
	      a.style.display = "none";
	    }
	  });
	}
	const obs = new MutationObserver(() => hide());
	obs.observe(parent.document.body, { subtree: true, childList: true });
	hide();
	</script>
	"""
	html(js, height=0)
except Exception:
	pass
