import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Search, User, Mail, Hash, Calendar, ShieldCheck, Phone, Edit2, Save, X } from 'lucide-react';

const getStatusColor = (s) => {
  const st = s?.toLowerCase() || '';
  if (st.includes('manter')) return '#28a745'; // Verde clássico
  if (st.includes('analise')) return '#ffc107'; // Amarelo clássico
  return '#dc3545'; // Vermelho clássico
};

const styles = {
  container: { maxWidth: '900px', margin: '40px auto', padding: '0 20px', fontFamily: '"Inter", sans-serif' },
  header: { textAlign: 'center', marginBottom: '40px' },
  title: { fontSize: '32px', fontWeight: '800', color: '#64748b', margin: 0 }, // Mesma cor do subtítulo
  subtitle: { color: '#64748b', fontSize: '16px', marginTop: '5px' },
  
  // Barra de pesquisa mais clara e com botão azul
  searchBox: { display: 'flex', gap: '10px', background: '#fff', padding: '8px', borderRadius: '16px', boxShadow: '0 4px 15px rgba(0,0,0,0.05)', border: '1px solid #e2e8f0', marginBottom: '40px' },
  searchInput: { flex: 1, border: 'none', padding: '10px 15px', fontSize: '16px', outline: 'none', color: '#1a1a1a' },
  searchBtn: { background: '#007bff', color: '#fff', border: 'none', padding: '0 25px', borderRadius: '12px', fontWeight: '600', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '8px' },
  
  card: { background: '#fff', borderRadius: '24px', padding: '40px', boxShadow: '0 10px 30px rgba(0,0,0,0.08)', position: 'relative' },
  cardHeader: { display: 'flex', alignItems: 'center', gap: '20px', marginBottom: '30px', paddingBottom: '25px', borderBottom: '2px solid #f1f5f9' },
  avatar: { width: '60px', height: '60px', borderRadius: '14px', display: 'flex', alignItems: 'center', justifyContent: 'center' },
  nome: { fontSize: '26px', fontWeight: '800', color: '#1a1a1a', margin: 0 },
  badge: { padding: '6px 14px', borderRadius: '30px', fontSize: '11px', fontWeight: '800', display: 'inline-flex', alignItems: 'center', textTransform: 'uppercase' },
  actions: { display: 'flex', gap: '10px', marginLeft: 'auto' }, // Botões encostados à direita
  grid: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '15px' },
  infoItem: { background: '#f8fafc', padding: '15px', borderRadius: '16px', display: 'flex', gap: '12px', border: '1px solid #f1f5f9' },
  label: { fontSize: '10px', textTransform: 'uppercase', color: '#94a3b8', fontWeight: '800', display: 'block', marginBottom: '3px' },
  val: { fontSize: '15px', fontWeight: '600', color: '#334155', wordBreak: 'break-all' },
  
  // Campos de edição com correção do calendário (colorScheme)
  fieldInput: { width: '100%', padding: '10px', borderRadius: '8px', border: '1px solid #cbd5e1', backgroundColor: '#fff', color: '#1a1a1a', fontSize: '14px', outline: 'none' },
  dateInput: { width: '100%', padding: '10px', borderRadius: '8px', border: '1px solid #cbd5e1', backgroundColor: '#fff', color: '#1a1a1a', fontSize: '14px', outline: 'none', colorScheme: 'light' },
  editInputName: { fontSize: '24px', fontWeight: '800', border: '1px solid #cbd5e1', borderRadius: '8px', padding: '8px', width: '100%', color: '#1a1a1a', backgroundColor: '#fff' },
  
  editBtn: { background: '#f1f5f9', color: '#334155', border: 'none', padding: '10px 18px', borderRadius: '10px', cursor: 'pointer', fontWeight: '600', display: 'flex', alignItems: 'center', gap: '8px' },
  saveBtn: { background: '#28a745', color: '#fff', border: 'none', padding: '10px 20px', borderRadius: '10px', cursor: 'pointer', fontWeight: '600', display: 'flex', alignItems: 'center', gap: '8px' },
  cancelBtn: { background: '#dc3545', color: '#fff', border: 'none', padding: '10px', borderRadius: '10px', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' },
  errorCard: { textAlign: 'center', padding: '50px', background: '#fff', borderRadius: '24px', boxShadow: '0 10px 20px rgba(0,0,0,0.05)' }
};

export default function App() {
  const [alunos, setAlunos] = useState([]);
  const [busca, setBusca] = useState("");
  const [aluno, setAluno] = useState(null);
  const [editMode, setEditMode] = useState(false);
  const [temp, setTemp] = useState(null);

  const carregar = () => {
    axios.get('http://127.0.0.1:5000/api/alunos')
      .then(res => setAlunos(res.data))
      .catch(err => console.log(err));
  };

  useEffect(() => { carregar(); }, []);

  const buscar = (e) => {
    e.preventDefault();
    const t = busca.toLowerCase().trim();
    if (!t) return;
    const achado = alunos.find(a => 
      (a.nome || "").toLowerCase().includes(t) || 
      (a.matricula || "").toLowerCase().includes(t) ||
      (a.email || "").toLowerCase().includes(t)
    );
    setAluno(achado || "erro");
    setEditMode(false);
  };

  const salvar = async () => {
    try {
      await axios.post('http://127.0.0.1:5000/api/alunos/update', temp);
      setAluno(temp);
      setEditMode(false);
      carregar();
      alert("Sucesso ao salvar!");
    } catch (err) { alert("Erro ao salvar."); }
  };

  return (
    <div style={styles.container}>
      <header style={styles.header}>
        <h1 style={styles.title}>PD Reports</h1>
        <p style={styles.subtitle}>Gestão de Alunos</p>
      </header>

      <form onSubmit={buscar} style={styles.searchBox}>
        <input 
          style={styles.searchInput} 
          placeholder="Pesquisar por nome, e-mail ou matrícula..." 
          value={busca} 
          onChange={e => setBusca(e.target.value)} 
        />
        <button type="submit" style={styles.searchBtn}>
          <Search size={20} /> Buscar
        </button>
      </form>

      {aluno && aluno !== "erro" && (
        <div style={{ ...styles.card, borderLeft: `8px solid ${getStatusColor(aluno.status)}` }}>
          <div style={styles.cardHeader}>
            <div style={{ ...styles.avatar, backgroundColor: getStatusColor(aluno.status) + '15' }}>
              <User size={30} color={getStatusColor(aluno.status)} />
            </div>
            <div style={{ flex: 1 }}>
              {editMode ? (
                <input style={styles.editInputName} value={temp.nome} onChange={e => setTemp({ ...temp, nome: e.target.value })} />
              ) : (
                <h2 style={styles.nome}>{aluno.nome}</h2>
              )}
              {editMode ? (
                <select style={{...styles.fieldInput, width: 'auto', marginTop: '10px'}} value={temp.status} onChange={e => setTemp({...temp, status: e.target.value})}>
                  <option value="MANTER">MANTER</option>
                  <option value="EM ANALISE">EM ANALISE</option>
                  <option value="REMOVIDOS">REMOVIDOS</option>
                  <option value="DESLIGADO">DESLIGADO</option>
                </select>
              ) : (
                <span style={{ ...styles.badge, color: getStatusColor(aluno.status), backgroundColor: getStatusColor(aluno.status) + '15', border: `1px solid ${getStatusColor(aluno.status)}30` }}>
                  {aluno.status}
                </span>
              )}
            </div>
            <div style={styles.actions}>
              {editMode ? (
                <>
                  <button onClick={salvar} style={styles.saveBtn}><Save size={18} /> Salvar</button>
                  <button onClick={() => setEditMode(false)} style={styles.cancelBtn}><X size={18} /></button>
                </>
              ) : (
                <button onClick={() => { setTemp(aluno); setEditMode(true); }} style={styles.editBtn}><Edit2 size={18} /> Editar</button>
              )}
            </div>
          </div>

          <div style={styles.grid}>
            <div style={styles.infoItem}>
              <Hash size={18} color={getStatusColor(aluno.status)} />
              <div style={{width: '100%'}}>
                <span style={styles.label}>Matrícula</span>
                <span style={styles.val}>{aluno.matricula}</span>
              </div>
            </div>

            <div style={styles.infoItem}>
              <Phone size={18} color={getStatusColor(aluno.status)} />
              <div style={{width: '100%'}}>
                <span style={styles.label}>Telefone</span>
                {editMode ? <input style={styles.fieldInput} value={temp.telefone} onChange={e => setTemp({...temp, telefone: e.target.value})} /> : <span style={styles.val}>{aluno.telefone}</span>}
              </div>
            </div>

            <div style={{ ...styles.infoItem, gridColumn: '1 / -1' }}>
              <Mail size={18} color={getStatusColor(aluno.status)} />
              <div style={{width: '100%'}}>
                <span style={styles.label}>E-mail</span>
                {editMode ? <input style={styles.fieldInput} value={temp.email} onChange={e => setTemp({...temp, email: e.target.value})} /> : <span style={styles.val}>{aluno.email}</span>}
              </div>
            </div>

            <div style={styles.infoItem}>
              <Calendar size={18} color={getStatusColor(aluno.status)} />
              <div style={{width: '100%'}}>
                <span style={styles.label}>Nascimento e Idade</span>
                {editMode ? (
                  <input type="date" style={styles.dateInput} value={temp.nascimento} onChange={e => setTemp({ ...temp, nascimento: e.target.value })} />
                ) : (
                  <span style={styles.val}>{aluno.nascimento_formatado} {aluno.idade !== "-" && `(${aluno.idade} anos)`}</span>
                )}
              </div>
            </div>

            {/* Monitor na Grelha Principal */}
            <div style={styles.infoItem}>
              <ShieldCheck size={18} color={getStatusColor(aluno.status)} />
              <div style={{width: '100%'}}>
                <span style={styles.label}>Monitor Responsável</span>
                {editMode ? (
                  <select style={styles.fieldInput} value={temp.monitor} onChange={e => setTemp({...temp, monitor: e.target.value})}>
                    <option value="">Selecione...</option>
                    {["Alex", "André", "Douglas", "Gabriel", "Kellen", "Natanael"].map(m => <option key={m} value={m}>{m}</option>)}
                  </select>
                ) : (
                  <span style={styles.val}>{aluno.monitor || 'Não informado'}</span>
                )}
              </div>
            </div>

          </div>
        </div>
      )}

      {aluno === "erro" && (
        <div style={styles.errorCard}>
          <X size={48} color="#dc3545" />
          <p style={{fontWeight: 'bold', marginTop: '10px', color: '#1a1a1a'}}>Aluno não encontrado.</p>
        </div>
      )}
    </div>
  );
}