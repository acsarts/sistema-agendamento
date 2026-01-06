import streamlit as st
import pandas as pd

# Configuração da página
st.set_page_config(page_title="Sistema de Agendamento", layout="wide")

st.title("📅 Sistema de Agendamento Inteligente")
st.markdown("Cole sua lista de aulas abaixo e clique no botão para gerar a grade.")

# ==========================================
# 1. INPUT DE DADOS NA TELA
# ==========================================
texto_padrao = """Kátia Lima, 09:30 às 12:00; 
Ludimilla Costa, 13:00 às 15:00; 
Ludimilla Costa, 16:00 às 18:00; 
Mário Elesbão Lima Da Silva, 18:30 às 21:00;"""

lista_input = st.text_area("Cole a lista aqui (separe por ; ou nova linha):", value=texto_padrao, height=200)

# Botão de Ação
botao_gerar = st.button("🚀 Gerar Grade")

# ==========================================
# 2. CONFIGURAÇÃO (Fica escondido do usuário final, mas está no código)
# ==========================================
regras_estudios = {
    '2 PKS': {'abertura': '07:30', 'fechamento': '22:30', 'intervalos': [], 'proibido': ['Pós-Graduação', 'Graduação']},
    '3 PKS': {'abertura': '07:30', 'fechamento': '22:30', 'intervalos': [], 'proibido': []},
    '4 PKS': {'abertura': '08:30', 'fechamento': '21:00', 'intervalos': [], 'proibido': []},
    '6 PKS': {'abertura': '07:30', 'fechamento': '22:30', 'intervalos': [('12:00', '13:30'), ('17:00', '18:30')], 'proibido': []},
    '7 PKS': {'abertura': '07:00', 'fechamento': '23:00', 'intervalos': [], 'proibido': []},
    '8 PKS': {'abertura': '07:00', 'fechamento': '23:00', 'intervalos': [], 'proibido': []},
    '9 PKS': {'abertura': '07:30', 'fechamento': '22:30', 'intervalos': [('12:00', '13:30'), ('17:00', '18:30')], 'proibido': []},
    '11 SEDE': {'abertura': '07:00', 'fechamento': '23:00', 'intervalos': [], 'proibido': []},
    '12 SE//DE': {'abertura': '07:00', 'fechamento': '23:00', 'intervalos': [], 'proibido': []}
}

# ==========================================
# 3. FUNÇÕES AUXILIARES
# ==========================================
def converte_minutos(horario_str):
    try:
        h, m = map(int, horario_str.strip().split(':'))
        return h * 60 + m
    except:
        return -1

def verifica_colisao(inicio1, fim1, inicio2, fim2):
    return max(inicio1, inicio2) < min(fim1, fim2)

def buscar_sugestoes(aula, regras, ocupacoes):
    duracao = aula['fim'] - aula['inicio']
    sugestoes = []
    for nome, regra in regras.items():
        if any(p.lower() in aula['tipo'].lower() for p in regra['proibido']): continue
        abertura = converte_minutos(regra['abertura'])
        fechamento = converte_minutos(regra['fechamento'])
        
        for t_ini in range(abertura, fechamento, 30):
            t_fim = t_ini + duracao
            if t_fim > fechamento: break
            
            # Checa intervalos
            if any(verifica_colisao(t_ini, t_fim, converte_minutos(i[0]), converte_minutos(i[1])) for i in regra['intervalos']): continue
            # Checa ocupacao
            if any(verifica_colisao(t_ini, t_fim, oc['inicio'], oc['fim']) for oc in ocupacoes[nome]): continue
            
            h_txt = f"{t_ini//60:02d}:{t_ini%60:02d}"
            f_txt = f"{t_fim//60:02d}:{t_fim%60:02d}"
            sugestoes.append(f"{h_txt} - {f_txt} ({nome})")
            break # Uma sugestão por estúdio
    return sugestoes

# ==========================================
# 4. LÓGICA PRINCIPAL (Só roda se apertar o botão)
# ==========================================
if botao_gerar:
    texto_ajustado = lista_input.replace(';', '\n')
    linhas = [x.strip() for x in texto_ajustado.strip().split('\n')]
    aulas = []

    for linha in linhas:
        if not linha: continue
        partes = [p.strip() for p in linha.split(',')]
        if len(partes) >= 2:
            nome = partes[0]
            if 'às' in partes[1]:
                h_split = partes[1].split('às')
                tipo = partes[2] if len(partes) > 2 else "Geral"
                aulas.append({
                    'prof': nome, 'inicio': converte_minutos(h_split[0]), 'fim': converte_minutos(h_split[1]),
                    'tipo': tipo, 'orig_inicio': h_split[0].strip(), 'orig_fim': h_split[1].strip()
                })

    aulas.sort(key=lambda x: x['inicio'])
    agenda_final = []
    nao_agendados = []
    ocupacao_estudios = {k: [] for k in regras_estudios.keys()}

    # Agendamento
    for aula in aulas:
        agendado = False
        for nome_estudio, regras in regras_estudios.items():
            abertura = converte_minutos(regras['abertura'])
            fechamento = converte_minutos(regras['fechamento'])
            
            if aula['inicio'] < abertura or aula['fim'] > fechamento: continue
            if any(p.lower() in aula['tipo'].lower() for p in regras['proibido']): continue
            
            # Intervalos e Ocupação
            if any(verifica_colisao(aula['inicio'], aula['fim'], converte_minutos(i[0]), converte_minutos(i[1])) for i in regras['intervalos']): continue
            if any(verifica_colisao(aula['inicio'], aula['fim'], oc['inicio'], oc['fim']) for oc in ocupacao_estudios[nome_estudio]): continue
            
            ocupacao_estudios[nome_estudio].append(aula)
            agenda_final.append({'Sala': nome_estudio, 'Horário': f"{aula['orig_inicio']} - {aula['orig_fim']}", 'Professor': aula['prof'], 'Tipo': aula['tipo']})
            agendado = True
            break
        
        if not agendado: nao_agendados.append(aula)

    # ==========================
    # MOSTRAR RESULTADOS
    # ==========================
    if agenda_final:
        st.success("✅ Grade Gerada com Sucesso!")
        df = pd.DataFrame(agenda_final).sort_values(by=['Sala', 'Horário'])
        st.dataframe(df, use_container_width=True)
    else:
        st.warning("Nenhuma aula pôde ser agendada.")

    if nao_agendados:
        st.error(f"🚨 Conflitos Encontrados: {len(nao_agendados)}")
        for a in nao_agendados:
            with st.expander(f"❌ {a['prof']} ({a['orig_inicio']} - {a['orig_fim']})"):
                st.write(f"**Motivo:** Sem vaga no horário original.")
                sugs = buscar_sugestoes(a, regras_estudios, ocupacao_estudios)
                if sugs:
                    st.write("💡 **Sugestões de Reencaixe:**")
                    for s in sugs:
                        st.code(s, language="text")
                else:
                    st.write("⚠️ Nenhuma vaga alternativa encontrada.")
