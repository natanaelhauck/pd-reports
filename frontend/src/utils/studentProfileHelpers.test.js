import { describe, expect, it } from 'vitest';
import { MONITORES, STATUS_OPTIONS } from '../constants/studentProfileOptions.js';
import {
  CAMPOS_PERFIL_FORM,
  PERFIL_CADASTRO_INICIAL,
  ajustarQuantidadeFilhos,
  boolFromSelect,
  boolSelectValue,
  filhosResumo,
  montarPayloadPerfil,
  normalizarMonitor,
  normalizarPerfil,
  normalizarStatus,
  parseFilhos,
  perfilCadastroTemDados,
  quantidadeFromFilhos,
  stringifyFilhos,
} from './studentProfileHelpers.js';

describe('studentProfileHelpers', () => {
  describe('normalizarStatus', () => {
    it('normaliza status conhecidos sem mudar os valores usados pela UI', () => {
      expect(normalizarStatus(' manter ')).toBe(STATUS_OPTIONS[0]);
      expect(normalizarStatus('em analise')).toBe(STATUS_OPTIONS[1]);
      expect(normalizarStatus('remover')).toBe(STATUS_OPTIONS[2]);
      expect(normalizarStatus('desligada')).toBe(STATUS_OPTIONS[3]);
    });

    it('retorna string vazia para valores vazios ou desconhecidos', () => {
      expect(normalizarStatus('')).toBe('');
      expect(normalizarStatus(null)).toBe('');
      expect(normalizarStatus(undefined)).toBe('');
      expect(normalizarStatus('status ficticio')).toBe('');
    });
  });

  describe('normalizarMonitor', () => {
    it('normaliza nomes e e-mails de monitores conhecidos', () => {
      expect(normalizarMonitor('Alex')).toBe(MONITORES[0]);
      expect(normalizarMonitor('andre.monitor@example.com')).toBe(MONITORES[1]);
      expect(normalizarMonitor('Natanael123')).toBe(MONITORES[5]);
    });

    it('retorna string vazia para monitor vazio ou desconhecido', () => {
      expect(normalizarMonitor('')).toBe('');
      expect(normalizarMonitor(null)).toBe('');
      expect(normalizarMonitor('Monitor Teste')).toBe('');
    });
  });

  describe('campos booleanos de select', () => {
    it('converte booleanos para valores do select', () => {
      expect(boolSelectValue(true)).toBe('sim');
      expect(boolSelectValue(false)).toBe('nao');
      expect(boolSelectValue(null)).toBe('');
      expect(boolSelectValue(undefined)).toBe('');
    });

    it('converte valores do select para booleanos ou null', () => {
      expect(boolFromSelect('sim')).toBe(true);
      expect(boolFromSelect('nao')).toBe(false);
      expect(boolFromSelect('')).toBe(null);
      expect(boolFromSelect(undefined)).toBe(null);
    });
  });

  describe('helpers de filhos', () => {
    it('trata entrada vazia sem quebrar', () => {
      expect(parseFilhos('')).toEqual({ filhos: [], textoLivre: '' });
      expect(quantidadeFromFilhos([])).toBe('');
      expect(filhosResumo('')).toEqual(['Não informado']);
    });

    it('parseia e serializa a lista de filhos no formato atual', () => {
      const filhos = [
        { nome: 'Filho Teste 1', idade: '3' },
        { nome: 'Filho Teste 2', idade: '7' },
      ];
      const serializado = stringifyFilhos(filhos);

      expect(serializado).toBe('[{"nome":"Filho Teste 1","idade":"3"},{"nome":"Filho Teste 2","idade":"7"}]');
      expect(parseFilhos(serializado)).toEqual({ filhos, textoLivre: '' });
      expect(quantidadeFromFilhos(filhos)).toBe('2');
    });

    it('preserva texto livre legado quando nao for JSON', () => {
      expect(parseFilhos('dois filhos')).toEqual({ filhos: [], textoLivre: 'dois filhos' });
      expect(filhosResumo('dois filhos')).toEqual(['dois filhos']);
    });

    it('ajusta quantidade de filhos preservando entradas existentes', () => {
      const atuais = [{ nome: 'Filho Teste', idade: '5' }];

      expect(ajustarQuantidadeFilhos('3', atuais)).toEqual([
        { nome: 'Filho Teste', idade: '5' },
        { nome: '', idade: '' },
        { nome: '', idade: '' },
      ]);
      expect(ajustarQuantidadeFilhos('', atuais)).toEqual([]);
      expect(ajustarQuantidadeFilhos('6+', atuais)).toHaveLength(6);
    });
  });

  describe('perfilCadastroTemDados', () => {
    it('retorna falso para perfil vazio ou apenas com strings vazias', () => {
      expect(perfilCadastroTemDados({})).toBe(false);
      expect(perfilCadastroTemDados({ analise_perfil: '   ', trabalha: null })).toBe(false);
    });

    it('retorna verdadeiro quando ha dado relevante ou booleano informado', () => {
      expect(perfilCadastroTemDados(PERFIL_CADASTRO_INICIAL())).toBe(true);
      expect(perfilCadastroTemDados({ analise_perfil: 'Aluno teste' })).toBe(true);
      expect(perfilCadastroTemDados({ trabalha: false })).toBe(true);
    });
  });

  describe('normalizarPerfil e montarPayloadPerfil', () => {
    it('normaliza perfil preenchendo campos ausentes com o modelo atual', () => {
      const perfil = normalizarPerfil({
        matricula: 'MATRICULA_TESTE',
        analise_perfil: 'Perfil ficticio',
        trabalha: true,
        campo_extra: 'ignorado',
      });

      expect(perfil.matricula).toBe('MATRICULA_TESTE');
      expect(perfil.analise_perfil).toBe('Perfil ficticio');
      expect(perfil.trabalha).toBe(true);
      expect(perfil).not.toHaveProperty('campo_extra');
      expect(Object.keys(perfil)).toEqual(['matricula', ...CAMPOS_PERFIL_FORM]);
    });

    it('monta payload preservando matricula e todos os campos esperados', () => {
      const payload = montarPayloadPerfil({
        analise_perfil: 'Perfil ficticio',
        tem_filhos: true,
        filhos_descricao: stringifyFilhos([{ nome: 'Filho Teste', idade: '4' }]),
        previsao_formacao_ano: '2026',
      }, 'MATRICULA_TESTE');

      expect(payload.matricula).toBe('MATRICULA_TESTE');
      expect(payload.analise_perfil).toBe('Perfil ficticio');
      expect(payload.tem_filhos).toBe(true);
      expect(payload.previsao_formacao_ano).toBe('2026');
      expect(Object.keys(payload)).toEqual(['matricula', ...CAMPOS_PERFIL_FORM]);
    });
  });
});
