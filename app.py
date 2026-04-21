import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import json
import base64
from pathlib import Path

# ==============================================================================
# CONFIGURAÇÃO DO GOOGLE SHEETS
# ==============================================================================

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

@st.cache_resource
def get_google_sheets_client():
    """Conecta ao Google Sheets usando credenciais"""
    try:
        credentials_dict = dict(st.secrets["gcp_service_account"])
        credentials = Credentials.from_service_account_info(
            credentials_dict,
            scopes=SCOPES
        )
        return gspread.authorize(credentials)
    except Exception as e:
        st.error(f"❌ Erro ao conectar com Google Sheets: {str(e)}")
        st.stop()

def get_spreadsheet():
    """Retorna a planilha configurada"""
    client = get_google_sheets_client()
    try:
        spreadsheet_url = st.secrets["spreadsheet"]["url"]
        return client.open_by_url(spreadsheet_url)
    except Exception as e:
        st.error(f"❌ Erro ao abrir planilha: {str(e)}")
        st.stop()

# ==============================================================================
# FUNÇÕES DE PERSISTÊNCIA (GOOGLE SHEETS)
# ==============================================================================

def load_config():
    """Carrega configurações da planilha"""
    try:
        sheet = get_spreadsheet().worksheet('Config')
        records = sheet.get_all_records()
        
        if not records:
            # Criar config padrão
            default_config = {
                'pix': '11999887766',
                'group_name': 'Vôlei da Turma',
                'admin_pass': 'volei2024',
                'recovery_code': '482916'
            }
            save_config(default_config)
            return default_config
        
        return records[0]
    except:
        # Se planilha Config não existe, retorna padrão
        return {
            'pix': '11999887766',
            'group_name': 'Vôlei da Turma',
            'admin_pass': 'volei2024',
            'recovery_code': '482916'
        }

def save_config(config):
    """Salva configurações na planilha"""
    try:
        sheet = get_spreadsheet().worksheet('Config')
        sheet.clear()
        
        # Cabeçalhos
        headers = ['pix', 'group_name', 'admin_pass', 'recovery_code']
        sheet.append_row(headers)
        
        # Dados
        row = [
            config.get('pix', ''),
            config.get('group_name', ''),
            config.get('admin_pass', ''),
            config.get('recovery_code', '')
        ]
        sheet.append_row(row)
    except Exception as e:
        st.error(f"Erro ao salvar configurações: {str(e)}")

def load_events():
    """Carrega eventos da planilha"""
    try:
        sheet = get_spreadsheet().worksheet('Eventos')
        records = sheet.get_all_records()
        
        events = []
        for record in records:
            if record.get('id'):  # Ignora linhas vazias
                # Carregar participantes
                participants = []
                if record.get('participants_json'):
                    try:
                        participants = json.loads(record['participants_json'])
                    except:
                        participants = []
                
                events.append({
                    'id': record['id'],
                    'name': record['name'],
                    'date': record['date'],
                    'time': record['time'],
                    'local': record['local'],
                    'price': float(record['price']),
                    'slots': int(record['slots']),
                    'participants': participants
                })
        
        return events
    except:
        return []

def save_event(event):
    """Salva ou atualiza um evento na planilha"""
    try:
        sheet = get_spreadsheet().worksheet('Eventos')
        
        # Buscar evento existente
        try:
            cell = sheet.find(event['id'])
            row_num = cell.row
        except:
            # Evento novo - adicionar no final
            row_num = len(sheet.get_all_values()) + 1
            
            # Se for primeira linha, adicionar cabeçalhos
            if row_num == 1:
                headers = ['id', 'name', 'date', 'time', 'local', 'price', 'slots', 'participants_json']
                sheet.append_row(headers)
                row_num = 2
        
        # Serializar participantes
        participants_json = json.dumps(event.get('participants', []), ensure_ascii=False)
        
        # Dados do evento
        row = [
            event['id'],
            event['name'],
            event['date'],
            event['time'],
            event['local'],
            event['price'],
            event['slots'],
            participants_json
        ]
        
        # Atualizar ou inserir
        if row_num <= len(sheet.get_all_values()):
            # Atualizar linha existente
            for col, value in enumerate(row, start=1):
                sheet.update_cell(row_num, col, value)
        else:
            # Adicionar nova linha
            sheet.append_row(row)
            
    except Exception as e:
        st.error(f"Erro ao salvar evento: {str(e)}")

def delete_event(event_id):
    """Remove um evento da planilha"""
    try:
        sheet = get_spreadsheet().worksheet('Eventos')
        cell = sheet.find(event_id)
        if cell:
            sheet.delete_rows(cell.row)
    except Exception as e:
        st.error(f"Erro ao excluir evento: {str(e)}")

# ==============================================================================
# CONFIGURAÇÃO DA PÁGINA
# ==============================================================================

st.set_page_config(
    page_title="Vôlei da Turma",
    page_icon="🏐",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# CSS customizado
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 2rem 0 1rem;
    }
    .logo-icon {
        font-size: 48px;
        margin-bottom: 8px;
    }
    .event-card {
        background: white;
        border: 0.5px solid #e0e0e0;
        border-radius: 12px;
        padding: 1.25rem;
        margin-bottom: 12px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .badge {
        display: inline-block;
        font-size: 11px;
        padding: 3px 10px;
        border-radius: 99px;
        font-weight: 500;
        margin: 4px 0;
    }
    .badge-open {
        background: #e1f5ee;
        color: #0f6e56;
    }
    .badge-full {
        background: #faece7;
        color: #993c1d;
    }
    .badge-waiting {
        background: #faeeda;
        color: #854f0b;
    }
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        font-weight: 500;
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# FUNÇÕES AUXILIARES
# ==============================================================================

def format_currency(value):
    """Formata valor para moeda brasileira"""
    return f"R$ {value:.2f}".replace('.', ',')

def format_date(date_str):
    """Formata data de YYYY-MM-DD para DD/MM/YYYY"""
    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        return date_obj.strftime('%d/%m/%Y')
    except:
        return date_str

def get_confirmed_count(event):
    """Retorna quantidade de participantes confirmados"""
    return len([p for p in event.get('participants', []) if p['status'] == 'confirmed'])

def get_available_slots(event):
    """Retorna vagas disponíveis"""
    return event['slots'] - get_confirmed_count(event)

def get_user_participation(event, username):
    """Verifica se usuário está participando do evento"""
    for p in event.get('participants', []):
        if p['name'] == username:
            return p
    return None

def save_receipt_base64(uploaded_file):
    """Salva comprovante como base64"""
    return base64.b64encode(uploaded_file.getbuffer()).decode()

# ==============================================================================
# INICIALIZAÇÃO DO SESSION STATE
# ==============================================================================

if 'config' not in st.session_state:
    st.session_state.config = load_config()

if 'events' not in st.session_state:
    st.session_state.events = load_events()

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if 'username' not in st.session_state:
    st.session_state.username = None

if 'is_admin' not in st.session_state:
    st.session_state.is_admin = False

if 'cart' not in st.session_state:
    st.session_state.cart = []

if 'failed_attempts' not in st.session_state:
    st.session_state.failed_attempts = 0

if 'current_view' not in st.session_state:
    st.session_state.current_view = 'login'

# ==============================================================================
# TELA DE LOGIN
# ==============================================================================

def show_login():
    st.markdown('<div class="main-header">', unsafe_allow_html=True)
    st.markdown('<div class="logo-icon">🏐</div>', unsafe_allow_html=True)
    st.markdown(f'<h1>{st.session_state.config["group_name"]}</h1>', unsafe_allow_html=True)
    st.markdown('<p style="color: #666;">Organize sua pelada sem complicação</p>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    with st.container():
        st.markdown('<div class="event-card">', unsafe_allow_html=True)
        
        name = st.text_input("Seu nome completo", key="login_name")
        
        role = st.radio("Entrar como", ["🏐 Jogador", "⚙️ Admin"], horizontal=True, key="role")
        
        password = None
        if role == "⚙️ Admin":
            password = st.text_input("Senha de administrador", type="password", key="admin_pass")
            
            if st.session_state.failed_attempts > 0:
                remaining = 3 - st.session_state.failed_attempts
                st.warning(f"⚠️ {remaining} tentativa(s) restante(s)")
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        if st.button("Entrar", type="primary"):
            if not name:
                st.error("❌ Forneça seu nome para continuar")
                return
            
            if role == "⚙️ Admin":
                if not password:
                    st.error("❌ Forneça a senha de admin para continuar")
                    return
                
                if password != st.session_state.config['admin_pass']:
                    st.session_state.failed_attempts += 1
                    
                    if st.session_state.failed_attempts >= 3:
                        st.session_state.current_view = 'reset_password'
                        st.rerun()
                    else:
                        st.error(f"❌ Senha incorreta. {3 - st.session_state.failed_attempts} tentativa(s) restante(s).")
                    return
                
                st.session_state.is_admin = True
            
            st.session_state.username = name
            st.session_state.logged_in = True
            st.session_state.current_view = 'admin' if st.session_state.is_admin else 'player'
            st.session_state.failed_attempts = 0
            st.rerun()

# ==============================================================================
# TELA DE RECUPERAÇÃO DE SENHA
# ==============================================================================

def show_reset_password():
    st.markdown('<div class="main-header">', unsafe_allow_html=True)
    st.markdown('<h2>Redefinir senha</h2>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.warning("⚠️ 3 tentativas incorretas. Use o código de recuperação.")
    
    recovery_code = st.text_input("Código de recuperação (6 dígitos)", type="password", max_chars=6)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("← Voltar"):
            st.session_state.current_view = 'login'
            st.session_state.failed_attempts = 0
            st.rerun()
    
    with col2:
        if st.button("Verificar código", type="primary"):
            if recovery_code == st.session_state.config['recovery_code']:
                st.session_state.current_view = 'new_password'
                st.rerun()
            else:
                st.error("❌ Código incorreto. Tente novamente.")

# ==============================================================================
# TELA DE NOVA SENHA
# ==============================================================================

def show_new_password():
    st.markdown('<div class="main-header">', unsafe_allow_html=True)
    st.markdown('<h2>Nova senha</h2>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.success("✅ Código verificado! Defina uma nova senha.")
    
    new_pass1 = st.text_input("Nova senha", type="password", key="new_pass1")
    new_pass2 = st.text_input("Confirmar nova senha", type="password", key="new_pass2")
    
    if st.button("Salvar nova senha", type="primary"):
        if not new_pass1 or new_pass1 != new_pass2:
            st.error("❌ As senhas não coincidem.")
            return
        
        st.session_state.config['admin_pass'] = new_pass1
        save_config(st.session_state.config)
        
        st.session_state.current_view = 'login'
        st.session_state.failed_attempts = 0
        st.success("✅ Senha redefinida com sucesso!")
        st.rerun()

# ==============================================================================
# TELA DO JOGADOR
# ==============================================================================

def show_player_view():
    st.markdown(f'<h3>Olá, {st.session_state.username} 👋</h3>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("🔄 Atualizar"):
            st.session_state.events = load_events()
            st.rerun()
    
    if st.button("Sair", key="logout_player"):
        st.session_state.logged_in = False
        st.session_state.username = None
        st.session_state.is_admin = False
        st.session_state.cart = []
        st.session_state.current_view = 'login'
        st.rerun()
    
    tab1, tab2 = st.tabs(["📅 Eventos", "🛒 Carrinho"])
    
    with tab1:
        show_player_events()
    
    with tab2:
        show_player_cart()

def show_player_events():
    """Exibe lista de eventos para o jogador"""
    events = st.session_state.events
    
    if not events:
        st.info("📭 Nenhum evento disponível ainda.")
        return
    
    for event in events:
        with st.container():
            st.markdown('<div class="event-card">', unsafe_allow_html=True)
            
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown(f"**{event['name']}**")
                st.markdown(f"<small>{format_date(event['date'])} às {event['time']} — {event['local']}</small>", unsafe_allow_html=True)
                st.markdown(f"**{format_currency(event['price'])}/ingresso**")
            
            with col2:
                available = get_available_slots(event)
                if available <= 0:
                    st.markdown('<span class="badge badge-full">Esgotado</span>', unsafe_allow_html=True)
                elif available <= 2:
                    st.markdown('<span class="badge badge-waiting">Últimas vagas</span>', unsafe_allow_html=True)
                else:
                    st.markdown('<span class="badge badge-open">Vagas abertas</span>', unsafe_allow_html=True)
            
            # Barra de progresso
            confirmed = get_confirmed_count(event)
            progress = confirmed / event['slots'] if event['slots'] > 0 else 0
            st.progress(progress)
            st.markdown(f"<small>{confirmed} confirmados • {available} vagas livres</small>", unsafe_allow_html=True)
            
            # Ações
            participation = get_user_participation(event, st.session_state.username)
            
            if participation:
                if participation['status'] == 'confirmed':
                    st.success("✅ Confirmado")
                else:
                    st.warning("⏳ Aguardando confirmação")
            elif event['id'] in st.session_state.cart:
                if st.button(f"Remover do carrinho", key=f"remove_{event['id']}"):
                    st.session_state.cart.remove(event['id'])
                    st.rerun()
            elif available > 0:
                if st.button(f"➕ Participar", key=f"add_{event['id']}", type="primary"):
                    st.session_state.cart.append(event['id'])
                    st.rerun()
            else:
                st.error("Esgotado")
            
            # Mostrar participantes confirmados
            if st.checkbox(f"Ver confirmados ({confirmed})", key=f"show_participants_{event['id']}"):
                confirmed_participants = [p for p in event.get('participants', []) if p['status'] == 'confirmed']
                for p in confirmed_participants:
                    col_a, col_b = st.columns([2, 1])
                    with col_a:
                        st.markdown(f"✓ {p['name']}")
                    with col_b:
                        if p.get('receipt_base64') and st.button("Ver comprovante", key=f"view_receipt_{event['id']}_{p['name']}"):
                            show_receipt_modal(p['name'], p['receipt_base64'])
            
            st.markdown('</div>', unsafe_allow_html=True)

def show_player_cart():
    """Exibe carrinho de compras do jogador"""
    if not st.session_state.cart:
        st.info("🛒 Nenhum evento no carrinho.\n\nVá em 'Eventos' e clique em '➕ Participar'.")
        return
    
    st.markdown("### Resumo dos ingressos")
    
    total = 0
    events_in_cart = []
    
    for event_id in st.session_state.cart:
        event = next((e for e in st.session_state.events if e['id'] == event_id), None)
        if event:
            events_in_cart.append(event)
            total += event['price']
            
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                st.markdown(f"**{event['name']}**")
                st.markdown(f"<small>{format_date(event['date'])} às {event['time']}</small>", unsafe_allow_html=True)
            with col2:
                st.markdown(f"**{format_currency(event['price'])}**")
            with col3:
                if st.button("✕", key=f"cart_remove_{event_id}"):
                    st.session_state.cart.remove(event_id)
                    st.rerun()
    
    st.divider()
    st.markdown(f"### Total: {format_currency(total)}")
    
    # Pix
    st.markdown("---")
    st.markdown("### Pagamento via Pix")
    
    pix_key = st.session_state.config['pix']
    st.info(f"**Chave Pix:** `{pix_key}`")
    
    if st.button("📋 Copiar chave Pix"):
        st.success("✅ Cole esta chave no app do seu banco!")
    
    # Upload de comprovante
    st.markdown("### Comprovante de pagamento")
    st.markdown("Anexe o comprovante do Pix para garantir sua vaga.")
    
    uploaded_file = st.file_uploader("Escolher arquivo", type=['png', 'jpg', 'jpeg', 'pdf'], key="receipt_upload")
    
    if uploaded_file:
        st.success(f"✅ Comprovante anexado: {uploaded_file.name}")
        
        if st.button("Confirmar e garantir vagas", type="primary"):
            # Converter para base64
            receipt_base64 = save_receipt_base64(uploaded_file)
            
            # Adicionar aos eventos
            for event in events_in_cart:
                if get_available_slots(event) > 0:
                    if 'participants' not in event:
                        event['participants'] = []
                    
                    event['participants'].append({
                        'name': st.session_state.username,
                        'status': 'confirmed',
                        'receipt_base64': receipt_base64,
                        'receipt_name': uploaded_file.name,
                        'timestamp': datetime.now().isoformat()
                    })
                    
                    # Salvar no Google Sheets
                    save_event(event)
            
            # Atualizar eventos localmente
            st.session_state.events = load_events()
            st.session_state.cart = []
            st.success("✅ Vaga confirmada! Seu comprovante foi salvo.")
            st.rerun()

def show_receipt_modal(name, receipt_base64):
    """Exibe comprovante"""
    st.markdown(f"### Comprovante — {name}")
    
    try:
        image_data = base64.b64decode(receipt_base64)
        st.image(image_data, use_container_width=True)
    except:
        st.error("❌ Erro ao carregar comprovante")

# ==============================================================================
# TELA DO ADMIN
# ==============================================================================

def show_admin_view():
    st.markdown(f'<h3>⚙️ Admin — {st.session_state.username}</h3>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("🔄 Atualizar"):
            st.session_state.events = load_events()
            st.session_state.config = load_config()
            st.rerun()
    
    if st.button("Sair", key="logout_admin"):
        st.session_state.logged_in = False
        st.session_state.username = None
        st.session_state.is_admin = False
        st.session_state.current_view = 'login'
        st.rerun()
    
    tab1, tab2, tab3 = st.tabs(["📅 Eventos", "➕ Novo evento", "⚙️ Configurações"])
    
    with tab1:
        show_admin_events()
    
    with tab2:
        show_create_event()
    
    with tab3:
        show_admin_config()

def show_admin_events():
    """Exibe eventos para o admin"""
    events = st.session_state.events
    
    if not events:
        st.info("📭 Nenhum evento criado ainda.")
        return
    
    for event in events:
        with st.expander(f"**{event['name']}** — {format_date(event['date'])}", expanded=False):
            confirmed = get_confirmed_count(event)
            pending = len([p for p in event.get('participants', []) if p['status'] == 'pending'])
            available = get_available_slots(event)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Confirmados", f"{confirmed}/{event['slots']}")
            with col2:
                st.metric("Aguardando", pending)
            with col3:
                st.metric("Arrecadado", format_currency(confirmed * event['price']))
            
            st.divider()
            
            # Participantes aguardando
            pending_participants = [p for p in event.get('participants', []) if p['status'] == 'pending']
            if pending_participants:
                st.markdown("**Aguardando confirmação:**")
                for p in pending_participants:
                    col_a, col_b, col_c = st.columns([2, 1, 1])
                    with col_a:
                        st.markdown(f"{p['name']}")
                        if p.get('receipt_base64'):
                            if st.button(f"Ver comprovante", key=f"admin_receipt_{event['id']}_{p['name']}"):
                                show_receipt_modal(p['name'], p['receipt_base64'])
                    with col_b:
                        if st.button("✅", key=f"confirm_{event['id']}_{p['name']}"):
                            for participant in event['participants']:
                                if participant['name'] == p['name']:
                                    participant['status'] = 'confirmed'
                            save_event(event)
                            st.session_state.events = load_events()
                            st.rerun()
                    with col_c:
                        if st.button("❌", key=f"reject_{event['id']}_{p['name']}"):
                            event['participants'] = [x for x in event['participants'] if x['name'] != p['name']]
                            save_event(event)
                            st.session_state.events = load_events()
                            st.rerun()
                st.divider()
            
            # Confirmados
            confirmed_participants = [p for p in event.get('participants', []) if p['status'] == 'confirmed']
            if confirmed_participants:
                st.markdown(f"**Confirmados ({len(confirmed_participants)}):**")
                for p in confirmed_participants:
                    col_a, col_b = st.columns([3, 1])
                    with col_a:
                        st.markdown(f"✓ {p['name']}")
                    with col_b:
                        if p.get('receipt_base64') and st.button("Ver", key=f"admin_conf_receipt_{event['id']}_{p['name']}"):
                            show_receipt_modal(p['name'], p['receipt_base64'])
            
            st.divider()
            
            if st.button("🗑️ Excluir evento", key=f"delete_{event['id']}"):
                delete_event(event['id'])
                st.session_state.events = load_events()
                st.rerun()

def show_create_event():
    """Formulário para criar novo evento"""
    st.markdown("### Criar novo evento")
    
    name = st.text_input("Nome do evento", placeholder="Ex: Vôlei — 22/06")
    
    col1, col2 = st.columns(2)
    with col1:
        date = st.date_input("Data")
    with col2:
        time = st.time_input("Horário")
    
    local = st.text_input("Local", placeholder="Ex: Arena Vôlei — Quadra 2")
    
    col3, col4 = st.columns(2)
    with col3:
        price = st.number_input("Ingresso (R$)", min_value=0.0, step=0.50, format="%.2f")
    with col4:
        slots = st.number_input("Limite de vagas", min_value=1, step=1)
    
    if st.button("Criar evento", type="primary"):
        if not name or not local:
            st.error("❌ Preencha todos os campos.")
            return
        
        new_event = {
            'id': f"ev_{int(datetime.now().timestamp())}",
            'name': name,
            'date': date.strftime('%Y-%m-%d'),
            'time': time.strftime('%H:%M'),
            'local': local,
            'price': float(price),
            'slots': int(slots),
            'participants': []
        }
        
        save_event(new_event)
        st.session_state.events = load_events()
        
        st.success("✅ Evento criado com sucesso!")
        st.rerun()

def show_admin_config():
    """Configurações do admin"""
    st.markdown("### Configurações gerais")
    
    pix = st.text_input("Chave Pix do grupo", value=st.session_state.config['pix'])
    group_name = st.text_input("Nome do grupo", value=st.session_state.config['group_name'])
    recovery_code = st.text_input("Código de recuperação (6 dígitos)", value=st.session_state.config['recovery_code'], max_chars=6)
    new_pass = st.text_input("Nova senha de admin", type="password", placeholder="Deixe em branco para não alterar")
    
    if st.button("Salvar configurações", type="primary"):
        if pix:
            st.session_state.config['pix'] = pix
        if group_name:
            st.session_state.config['group_name'] = group_name
        if recovery_code:
            st.session_state.config['recovery_code'] = recovery_code
        if new_pass:
            st.session_state.config['admin_pass'] = new_pass
        
        save_config(st.session_state.config)
        st.success("✅ Configurações salvas!")

# ==============================================================================
# ROTEAMENTO PRINCIPAL
# ==============================================================================

def main():
    if st.session_state.current_view == 'login':
        show_login()
    elif st.session_state.current_view == 'reset_password':
        show_reset_password()
    elif st.session_state.current_view == 'new_password':
        show_new_password()
    elif st.session_state.logged_in:
        if st.session_state.is_admin:
            show_admin_view()
        else:
            show_player_view()

if __name__ == "__main__":
    main()
