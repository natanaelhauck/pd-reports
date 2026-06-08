import { useEffect, useState } from 'react';
import axios from 'axios';
import { CourseCertificatesSection } from './CourseCertificatesSection.jsx';
import { CourseHoursStudentCard } from './CourseHoursStudentCard.jsx';
import { CourseScheduleSection } from './CourseScheduleSection.jsx';

export function CourseHoursStudentDetails({ aluno, apiBaseUrl, authHeaders }) {
  const [dados, setDados] = useState(null);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState('');

  useEffect(() => {
    if (!aluno?.matricula) return;
    let cancelado = false;

    const carregar = async () => {
      setCarregando(true);
      setErro('');
      setDados(null);
      try {
        const res = await axios.get(
          `${apiBaseUrl}/api/alunos/${encodeURIComponent(aluno.matricula)}/integralizacao`,
          { headers: authHeaders, timeout: 20000 },
        );
        if (!cancelado) setDados(res.data);
      } catch (err) {
        const mensagem = err.response?.data?.erro || 'Não foi possível carregar a integralização do aluno.';
        if (!cancelado) setErro(mensagem);
      } finally {
        if (!cancelado) setCarregando(false);
      }
    };

    carregar();
    return () => {
      cancelado = true;
    };
  }, [aluno?.matricula, apiBaseUrl, authHeaders]);

  if (carregando) {
    return <p className="monitoring-state">Carregando integralização...</p>;
  }

  if (erro) {
    return <p className="monitoring-state error">{erro}</p>;
  }

  if (!dados) {
    return null;
  }

  if (!dados.encontrado) {
    return (
      <section className="course-section">
        <div className="course-section-head">
          <div>
            <h3>Integralização</h3>
            <p>{dados.mensagem || 'Sem dados de integralização para este aluno.'}</p>
          </div>
        </div>
      </section>
    );
  }

  const alunoIntegralizacao = dados.aluno;

  return (
    <div className="course-hours-details">
      <CourseHoursStudentCard aluno={alunoIntegralizacao} compact />
      <CourseCertificatesSection certificados={alunoIntegralizacao.certificados} />
      <CourseScheduleSection aluno={alunoIntegralizacao} />
    </div>
  );
}
