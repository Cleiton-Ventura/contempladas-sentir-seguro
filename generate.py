"""
Gerador da página de Cartas Contempladas — Sentir Seguro Corretora
Busca dados dos parceiros, aplica comissão de 3% do crédito sobre a entrada, gera index.html
Exibe disponíveis (negociáveis) e reservadas (gatilho de escassez).
"""

import re
import sys
import requests
from datetime import datetime
from urllib.parse import quote

# ── Configurações ────────────────────────────────────────────────────────────
WHATSAPP  = '5583987253467'
COMISSAO  = 0.03   # 3% do crédito somado à entrada
OUTPUT    = 'index.html'

SOURCES = [
    {'url': 'https://contempladas.contemplasul.com.br/?segmento=imovel',
     'fonte': 'ContemplaSul', 'seg_fallback': 'Imóvel'},
    {'url': 'https://contempladas.contemplasul.com.br/?segmento=veiculo',
     'fonte': 'ContemplaSul', 'seg_fallback': 'Veículo'},
    {'url': 'https://contempladas.gauerconsorcios.com.br/?segmento=veiculo',
     'fonte': 'Gauer', 'seg_fallback': 'Veículo'},
]

HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/120.0.0.0 Safari/537.36'
    ),
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
}

LOGOS = {
    'itau':       'https://gauerconsorcios.contempladas.net/public/media/images/logos/administradoras/itauconsorcio.png',
    'magalu':     'https://gauerconsorcios.contempladas.net/public/media/images/logos/administradoras/magalu.png',
    'bradesco':   'https://contemplasul.contempladas.net/public/media/images/logos/administradoras/bradesco.png',
    'caixa':      'https://contemplasul.contempladas.net/public/media/images/logos/administradoras/caixa.png',
    'santander':  'https://contemplasul.contempladas.net/public/media/images/logos/administradoras/santander.png',
    'sicoob':     'https://contemplasul.contempladas.net/public/media/images/logos/administradoras/sicoob.png',
    'sicredi':    'https://contemplasul.contempladas.net/public/media/images/logos/administradoras/sicredi.png',
    'porto':      'https://contemplasul.contempladas.net/public/media/images/logos/administradoras/portoseguro.png',
    'volkswagen': 'https://contemplasul.contempladas.net/public/media/images/logos/administradoras/volkswagen.png',
    'yamaha':     'https://contemplasul.contempladas.net/public/media/images/logos/administradoras/yamaha.png',
    'embracon':   'https://contemplasul.contempladas.net/public/media/images/logos/administradoras/embracon.png',
    'rodobens':   'https://contemplasul.contempladas.net/public/media/images/logos/administradoras/rodobens.png',
    'randon':     'https://contemplasul.contempladas.net/public/media/images/logos/administradoras/randon.png',
}

# ── Helpers ──────────────────────────────────────────────────────────────────
def normalize(s):
    table = str.maketrans('ãâàáäêéèëîíìïôóòõöûúùüçñ', 'aaaaaaeeeeiiiiooooouuuucn')
    return s.lower().translate(table)

def parse_real(s):
    if not s:
        return 0.0
    cleaned = re.sub(r'R\$\s*', '', s).replace('.', '').replace(',', '.').strip()
    try:
        return float(cleaned)
    except ValueError:
        return 0.0

def format_real(v):
    formatted = f'{v:,.2f}'
    intpart, dec = formatted.split('.')
    intpart = intpart.replace(',', '.')
    return f'R$ {intpart},{dec}'

def logo_for(admin):
    lc = normalize(admin)
    for key, url in LOGOS.items():
        if key in lc:
            return url
    return ''

def initials(name):
    parts = name.split()[:2]
    return ''.join(p[0].upper() for p in parts if p)

# ── Parser ───────────────────────────────────────────────────────────────────
def parse_cotas(html, fonte, seg_fallback):
    cotas = []
    parts = re.split(r'Detalhes da cota \d+', html)

    for section in parts[1:]:
        kv = {}
        for m in re.finditer(
            r'([^<:\n\r]{2,50}):\s*<strong>([^<]{1,150})</strong>',
            section
        ):
            label_raw = re.sub(r'<[^>]+>', '', m.group(1)).strip()
            label = normalize(label_raw)
            if label:
                kv[label] = m.group(2).strip()

        situacao_norm = normalize(kv.get('situacao', ''))
        if 'disponiv' in situacao_norm:
            status = 'disponivel'
        elif 'reservad' in situacao_norm:
            status = 'reservada'
        else:
            continue  # ignora outros status

        administradora = kv.get('administradora', '')
        if not administradora:
            continue

        entrada_raw = kv.get('entrada', '')
        entrada_val = parse_real(entrada_raw)
        credito_raw = kv.get('credito', '')
        credito_val = parse_real(credito_raw)
        entrada_com_comissao = entrada_val + (credito_val * COMISSAO)

        cotas.append({
            'administradora': administradora,
            'codigo':         kv.get('codigo', ''),
            'segmento':       kv.get('segmento', seg_fallback),
            'fonte':          fonte,
            'logo':           logo_for(administradora),
            'credito':        credito_raw,
            'entrada':        format_real(entrada_com_comissao),
            'parcelas':       kv.get('parcelas', ''),
            'transferencia':  kv.get('transferencia', ''),
            'saldo':          kv.get('saldo devedor', ''),
            'vencimento':     kv.get('proximo vencimento', ''),
            'status':         status,
        })

    return cotas

# ── Fetch ─────────────────────────────────────────────────────────────────────
def fetch_all():
    cotas = []
    erros = []

    for src in SOURCES:
        try:
            r = requests.get(src['url'], headers=HEADERS, timeout=20)
            r.raise_for_status()
            found = parse_cotas(r.text, src['fonte'], src['seg_fallback'])
            disp = sum(1 for c in found if c['status'] == 'disponivel')
            resv = sum(1 for c in found if c['status'] == 'reservada')
            cotas.extend(found)
            print(f"✓ {src['fonte']} ({src['seg_fallback']}): {disp} disponíveis, {resv} reservadas")
        except Exception as e:
            erros.append(f"{src['fonte']} ({src['seg_fallback']})")
            print(f"✗ {src['fonte']} ({src['seg_fallback']}): {e}", file=sys.stderr)

    # Disponíveis primeiro, reservadas depois
    cotas.sort(key=lambda c: 0 if c['status'] == 'disponivel' else 1)
    return cotas, erros

# ── HTML builder ──────────────────────────────────────────────────────────────
WPP_SVG = '''<svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
  <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347z"/>
  <path d="M12 0C5.373 0 0 5.373 0 12c0 2.127.558 4.121 1.532 5.849L.057 23.527a.75.75 0 0 0 .916.916l5.68-1.476A11.934 11.934 0 0 0 12 24c6.627 0 12-5.373 12-12S18.627 0 12 0zm0 21.75a9.718 9.718 0 0 1-4.95-1.354l-.355-.212-3.68.955.98-3.574-.23-.368A9.72 9.72 0 0 1 2.25 12C2.25 6.615 6.615 2.25 12 2.25S21.75 6.615 21.75 12 17.385 21.75 12 21.75z"/>
</svg>'''

def card_html(c):
    seg_icon  = '🏠' if 'im' in c['segmento'].lower() else '🚗'
    ini       = initials(c['administradora'])
    logo      = c['logo']
    reservada = c['status'] == 'reservada'

    if reservada:
        msg = (
            f"Olá! Tenho interesse em entrar na lista de espera desta Carta Contemplada:\n\n"
            f"Administradora: {c['administradora']}\n"
            f"Código: {c['codigo']}\n"
            f"Segmento: {c['segmento']}\n"
            f"Crédito: {c['credito']}\n"
            f"Entrada: {c['entrada']}\n"
            f"Parcelas: {c['parcelas']}\n"
            f"Saldo devedor: {c['saldo']}\n"
            f"Próx. vencimento: {c['vencimento']}\n\n"
            f"Por favor, me avise quando esta cota ficar disponível."
        )
        top_class   = 'card-top card-top-reservada'
        badge_status = '<span class="badge badge-resv">🔒 Reservada</span>'
        btn_class   = 'btn-wpp btn-espera'
        btn_label   = 'Entrar na lista de espera'
        overlay     = '<div class="card-overlay"></div>'
    else:
        msg = (
            f"Olá! Tenho interesse nesta Carta Contemplada:\n\n"
            f"Administradora: {c['administradora']}\n"
            f"Código: {c['codigo']}\n"
            f"Segmento: {c['segmento']}\n"
            f"Crédito: {c['credito']}\n"
            f"Entrada: {c['entrada']}\n"
            f"Parcelas: {c['parcelas']}\n"
            f"Saldo devedor: {c['saldo']}\n"
            f"Próx. vencimento: {c['vencimento']}"
        )
        top_class   = 'card-top'
        badge_status = '<span class="badge badge-disp">✓ Disponível</span>'
        btn_class   = 'btn-wpp'
        btn_label   = 'Negociar no WhatsApp'
        overlay     = ''

    wpp      = f"https://api.whatsapp.com/send?phone={WHATSAPP}&text={quote(msg)}"
    logo_el  = (
        f'<img class="admin-logo" src="{logo}" alt="{c["administradora"]}" '
        f'onerror="this.style.display=\'none\';this.nextElementSibling.style.display=\'flex\'">'
        if logo else ''
    )

    return f'''
<div class="card" data-seg="{c["segmento"].lower()}" data-status="{c["status"]}">
  {overlay}
  <div class="{top_class}">
    <div class="card-admin">
      {logo_el}
      <div class="admin-fallback" style="{'display:none' if logo else ''}">{ini}</div>
      <div>
        <div class="admin-name">{c["administradora"]}</div>
        <div class="admin-sub">Cód. {c["codigo"]} &middot; {c["fonte"]}</div>
      </div>
    </div>
    <div class="card-badges">
      <span class="badge badge-seg">{seg_icon} {c["segmento"]}</span>
      {badge_status}
    </div>
  </div>
  <div class="card-body">
    <div>
      <span class="credito-val">{c["credito"]}</span>
      <span class="credito-label">de crédito</span>
    </div>
    <div class="divider"></div>
    <div class="row"><span class="row-label">Entrada</span><span class="row-val highlight">{c["entrada"]}</span></div>
    <div class="row"><span class="row-label">Parcelas</span><span class="row-val">{c["parcelas"] or "—"}</span></div>
    <div class="row"><span class="row-label">Saldo devedor</span><span class="row-val">{c["saldo"] or "—"}</span></div>
    <div class="row"><span class="row-label">Transferência</span><span class="row-val">{c["transferencia"] or "—"}</span></div>
    <div class="row"><span class="row-label">Próx. vencimento</span><span class="row-val">{c["vencimento"] or "—"}</span></div>
  </div>
  <div class="card-foot">
    <a class="{btn_class}" href="{wpp}" target="_blank" rel="noopener">
      {WPP_SVG}
      {btn_label}
    </a>
  </div>
</div>'''


def build_html(cotas, erros, updated_at):
    disponiveis = [c for c in cotas if c['status'] == 'disponivel']
    reservadas  = [c for c in cotas if c['status'] == 'reservada']
    imoveis     = sum(1 for c in cotas if 'im' in c['segmento'].lower())
    veiculos    = sum(1 for c in cotas if 've' in c['segmento'].lower())
    cards       = '\n'.join(card_html(c) for c in cotas)

    erro_banner = ''
    if erros:
        erro_banner = f'''
  <div class="error-bar">
    ⚠️ Não foi possível carregar: {", ".join(erros)}. Dados podem estar incompletos.
  </div>'''

    empty_msg = '' if cotas else '<div class="empty"><p>Nenhuma carta no momento. Volte em breve.</p></div>'

    return f'''<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Sentir Seguro Corretora — Cartas Contempladas</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    :root {{
      --blue: #1a4e8a; --blue-light: #2471c8;
      --orange: #b85c00; --orange-light: #e07820;
      --green-light: #27ae60; --accent: #f0a500;
      --bg: #f2f5f9; --white: #ffffff;
      --text: #1c2b3a; --muted: #6c7a8a; --border: #dce3ec;
      --shadow: 0 2px 14px rgba(0,0,0,.08); --radius: 12px;
    }}
    body {{ font-family: 'Segoe UI', system-ui, sans-serif; background: var(--bg); color: var(--text); min-height: 100vh; }}

    /* Header */
    header {{ background: linear-gradient(135deg, var(--blue) 0%, var(--blue-light) 100%); color: #fff; padding: 14px 24px; position: sticky; top: 0; z-index: 100; box-shadow: 0 3px 12px rgba(0,0,0,.2); }}
    .header-inner {{ max-width: 1280px; margin: 0 auto; display: flex; align-items: center; justify-content: space-between; gap: 16px; flex-wrap: wrap; }}
    .brand {{ display: flex; align-items: center; gap: 14px; }}
    .brand-logo {{ height: 44px; width: auto; display: block; }}
    .brand-divider {{ width: 1px; height: 36px; background: rgba(255,255,255,.35); }}
    .brand-sub {{ font-size: .8rem; opacity: .85; font-weight: 400; line-height: 1.3; }}
    .brand h1 {{ font-size: 1.25rem; font-weight: 700; }}
    .brand p  {{ font-size: .78rem; opacity: .8; margin-top: 2px; }}
    #last-updated {{ font-size: .75rem; opacity: .75; }}

    main {{ max-width: 1280px; margin: 0 auto; padding: 24px 16px 40px; }}

    /* Error */
    .error-bar {{ background: #fef3f2; border: 1px solid #fba8a0; border-radius: 8px; padding: 10px 16px; font-size: .83rem; color: #c0392b; margin-bottom: 16px; }}

    /* Filters */
    .filter-bar {{ display: flex; gap: 10px; align-items: center; margin-bottom: 18px; flex-wrap: wrap; }}
    .tabs {{ display: flex; background: var(--white); border-radius: 10px; padding: 4px; box-shadow: var(--shadow); gap: 4px; }}
    .tab {{ padding: 7px 16px; border: none; border-radius: 7px; cursor: pointer; font-size: .85rem; font-weight: 500; background: transparent; color: var(--muted); transition: all .2s; white-space: nowrap; }}
    .tab.active {{ background: var(--blue); color: #fff; }}
    .search-wrap {{ flex: 1; min-width: 180px; max-width: 280px; }}
    .search-wrap input {{ width: 100%; padding: 8px 14px; border: 1px solid var(--border); border-radius: 8px; font-size: .85rem; outline: none; background: var(--white); box-shadow: var(--shadow); }}
    .search-wrap input:focus {{ border-color: var(--blue-light); }}

    /* Stats */
    .stats {{ display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 20px; }}
    .stat {{ background: var(--white); border-radius: 10px; padding: 10px 18px; box-shadow: var(--shadow); font-size: .78rem; color: var(--muted); }}
    .stat strong {{ display: block; font-size: 1.35rem; font-weight: 700; color: var(--blue); line-height: 1.1; }}
    .stat.stat-resv strong {{ color: var(--orange); }}

    /* Grid */
    .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(290px, 1fr)); gap: 16px; }}

    /* Card */
    .card {{ background: var(--white); border-radius: var(--radius); box-shadow: var(--shadow); display: flex; flex-direction: column; overflow: hidden; transition: transform .2s, box-shadow .2s; position: relative; }}
    .card:hover {{ transform: translateY(-3px); box-shadow: 0 8px 24px rgba(0,0,0,.13); }}

    /* Reserved overlay */
    .card-overlay {{ position: absolute; inset: 0; background: repeating-linear-gradient(135deg, transparent, transparent 10px, rgba(0,0,0,.025) 10px, rgba(0,0,0,.025) 11px); pointer-events: none; z-index: 1; border-radius: var(--radius); }}

    /* Card top — disponível */
    .card-top {{ background: linear-gradient(135deg, var(--blue) 0%, var(--blue-light) 100%); padding: 13px 14px; display: flex; align-items: center; justify-content: space-between; gap: 10px; position: relative; z-index: 2; }}
    /* Card top — reservada */
    .card-top-reservada {{ background: linear-gradient(135deg, var(--orange) 0%, var(--orange-light) 100%); }}

    .card-admin {{ display: flex; align-items: center; gap: 10px; }}
    .admin-logo {{ width: 38px; height: 38px; object-fit: contain; background: #fff; border-radius: 7px; padding: 3px; flex-shrink: 0; }}
    .admin-fallback {{ width: 38px; height: 38px; background: rgba(255,255,255,.2); border-radius: 7px; display: flex; align-items: center; justify-content: center; font-size: .62rem; font-weight: 700; color: #fff; text-align: center; flex-shrink: 0; }}
    .admin-name {{ font-weight: 700; color: #fff; font-size: .9rem; }}
    .admin-sub  {{ font-size: .7rem; color: rgba(255,255,255,.65); margin-top: 1px; }}

    .card-badges {{ display: flex; flex-direction: column; align-items: flex-end; gap: 4px; }}
    .badge {{ font-size: .68rem; font-weight: 600; padding: 3px 9px; border-radius: 20px; white-space: nowrap; }}
    .badge-seg  {{ background: rgba(255,255,255,.2); color: #fff; }}
    .badge-disp {{ background: #2ecc71; color: #0b4a22; }}
    .badge-resv {{ background: #fff3cd; color: #7a4800; }}

    .card-body {{ padding: 16px; flex: 1; position: relative; z-index: 2; }}
    .credito-val   {{ font-size: 1.45rem; font-weight: 700; color: var(--blue); line-height: 1; }}
    .credito-label {{ font-size: .72rem; color: var(--muted); font-weight: 400; margin-left: 4px; }}
    .divider {{ height: 1px; background: var(--border); margin: 12px 0; }}
    .row {{ display: flex; justify-content: space-between; align-items: baseline; padding: 5px 0; font-size: .83rem; }}
    .row + .row {{ border-top: 1px solid #f0f3f7; }}
    .row-label {{ color: var(--muted); font-size: .75rem; }}
    .row-val   {{ font-weight: 600; text-align: right; }}
    .row-val.highlight {{ color: var(--green-light); font-size: .95rem; }}

    .card-foot {{ padding: 12px 14px; border-top: 1px solid var(--border); position: relative; z-index: 2; }}

    /* WPP buttons */
    .btn-wpp {{ display: flex; align-items: center; justify-content: center; gap: 8px; width: 100%; color: #fff; font-size: .87rem; font-weight: 700; padding: 11px; border-radius: 8px; border: none; cursor: pointer; text-decoration: none; transition: opacity .2s; }}
    .btn-wpp:hover {{ opacity: .9; }}
    .btn-wpp:not(.btn-espera) {{ background: linear-gradient(135deg, #25d366 0%, #128c7e 100%); }}
    .btn-espera {{ background: linear-gradient(135deg, var(--orange) 0%, var(--orange-light) 100%); font-size: .82rem; }}

    /* Empty */
    .empty {{ text-align: center; padding: 60px 20px; color: var(--muted); font-size: .9rem; }}

    /* Disclaimer */
    .disclaimer {{ background: #fff8e1; border-left: 3px solid var(--accent); border-radius: 6px; padding: 10px 14px; font-size: .76rem; color: #5a4000; margin-top: 28px; line-height: 1.5; }}

    footer {{ text-align: center; padding: 24px; font-size: .75rem; color: var(--muted); border-top: 1px solid var(--border); margin-top: 32px; }}

    @media (max-width: 600px) {{
      .brand h1 {{ font-size: 1rem; }}
      .grid {{ grid-template-columns: 1fr; }}
      .filter-bar {{ flex-direction: column; align-items: stretch; }}
      .search-wrap {{ max-width: 100%; }}
    }}
  </style>
</head>
<body>
<header>
  <div class="header-inner">
    <div class="brand">
      <img class="brand-logo" src="logo.png" alt="Sentir Seguro Corretora" onerror="this.style.display='none';this.nextElementSibling.style.display='block'">
      <div style="display:none">
        <h1>&#x1F6E1;&#xFE0F; Sentir Seguro Corretora</h1>
        <p>Cartas Contempladas</p>
      </div>
      <div class="brand-divider"></div>
      <span class="brand-sub">Cartas Contempladas<br>Im&oacute;vel &amp; Ve&iacute;culo</span>
    </div>
    <span id="last-updated">Atualizado em {updated_at}</span>
  </div>
</header>

<main>
  {erro_banner}

  <div class="filter-bar">
    <div class="tabs">
      <button class="tab active" data-tab="todos"      onclick="setTab(this)">Todos</button>
      <button class="tab"        data-tab="disponivel" onclick="setTab(this)">✅ Disponíveis</button>
      <button class="tab"        data-tab="reservada"  onclick="setTab(this)">🔒 Reservadas</button>
      <button class="tab"        data-tab="imovel"     onclick="setTab(this)">🏠 Imóvel</button>
      <button class="tab"        data-tab="veiculo"    onclick="setTab(this)">🚗 Veículo</button>
    </div>
    <div class="search-wrap">
      <input type="text" id="search" placeholder="Buscar administradora…" oninput="render()">
    </div>
  </div>

  <div class="stats">
    <div class="stat"><strong>{len(cotas)}</strong>Total</div>
    <div class="stat"><strong>{len(disponiveis)}</strong>Disponíveis</div>
    <div class="stat stat-resv"><strong>{len(reservadas)}</strong>Reservadas</div>
    <div class="stat"><strong>{imoveis}</strong>Imóveis</div>
    <div class="stat"><strong>{veiculos}</strong>Veículos</div>
    <div class="stat" id="stat-exibindo"><strong>{len(cotas)}</strong>Exibindo</div>
  </div>

  <div id="content">
    <div class="grid" id="grid">
      {cards}
    </div>
    {empty_msg}
  </div>

  <div class="disclaimer">
    ⚠️ Todas as informações devem ser <strong>confirmadas com nossa equipe comercial</strong> antes de qualquer contratação.
    Os valores de entrada apresentados incluem taxa de intermediação. Dados sujeitos a alteração sem aviso prévio.
  </div>
</main>

<footer>
  <p>Sentir Seguro Corretora &bull; (83) 9 8725-3467 &bull; Página atualizada diariamente</p>
</footer>

<script>
let activeTab = 'todos';
function setTab(btn) {{
  activeTab = btn.dataset.tab;
  document.querySelectorAll('.tab').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  render();
}}
function render() {{
  const q = (document.getElementById('search').value || '').toLowerCase().trim();
  let visible = 0;
  document.querySelectorAll('.card').forEach(card => {{
    const seg    = card.dataset.seg    || '';
    const status = card.dataset.status || '';
    const name   = card.querySelector('.admin-name')?.textContent.toLowerCase() || '';
    let show = true;
    if (activeTab === 'disponivel' && status !== 'disponivel') show = false;
    if (activeTab === 'reservada'  && status !== 'reservada')  show = false;
    if (activeTab === 'imovel'     && !seg.includes('im'))     show = false;
    if (activeTab === 'veiculo'    && !seg.includes('ve'))     show = false;
    if (q && !name.includes(q) && !seg.includes(q))           show = false;
    card.style.display = show ? '' : 'none';
    if (show) visible++;
  }});
  const el = document.getElementById('stat-exibindo');
  if (el) el.querySelector('strong').textContent = visible;
}}
</script>
</body>
</html>'''


# ── Main ─────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    print('Buscando cartas contempladas...')
    cotas, erros = fetch_all()
    disp = sum(1 for c in cotas if c['status'] == 'disponivel')
    resv = sum(1 for c in cotas if c['status'] == 'reservada')
    print(f'\nTotal: {len(cotas)} ({disp} disponíveis, {resv} reservadas)')

    now = datetime.now().strftime('%d/%m/%Y às %H:%M')
    html = build_html(cotas, erros, now)

    with open(OUTPUT, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f'✅ {OUTPUT} gerado com sucesso!')
    if erros:
        print(f'⚠️  Fontes com erro: {", ".join(erros)}')
