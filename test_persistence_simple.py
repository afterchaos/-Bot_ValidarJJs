#!/usr/bin/env python3
"""
Teste de Persistência de Dados (Versão Simples)

Este script testa o sistema de persistência de dados do bot de punições.
"""

import os
import sys
import json
import tempfile
from datetime import datetime

# Adiciona o caminho do projeto ao sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_manager import DataManager


def test_persistence_system():
    """
    Testa o sistema de persistência de dados.
    """
    print("Testando Sistema de Persistencia de Dados")
    print("=" * 50)
    
    # Cria um diretório temporário para testes
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"Diretorio de teste: {temp_dir}")
        
        # Inicializa o gerenciador de dados
        data_manager = DataManager(temp_dir)
        
        # Teste 1: Carregar dados vazios
        print("\nTeste 1: Carregar dados vazios")
        punishments, counter = data_manager.load_punishments()
        pending = data_manager.load_pending_punishments()
        
        assert len(punishments) == 0, "Deveria começar com 0 punições"
        assert counter == 1, "Contador deveria começar em 1"
        assert len(pending) == 0, "Deveria começar com 0 estados pendentes"
        print("Dados vazios carregados corretamente")
        
        # Teste 2: Salvar e carregar punições
        print("\nTeste 2: Salvar e carregar punições")
        test_punishments = {
            1: {
                "solicitante": 123456789,
                "punido": 987654321,
                "quantidade": 50,
                "motivo": "Teste de persistencia",
                "permissao": 111111111,
                "status": "pendente",
                "data": datetime.now().timestamp()
            },
            2: {
                "solicitante": 222222222,
                "punido": 333333333,
                "quantidade": 25,
                "motivo": "Outro teste",
                "permissao": 444444444,
                "status": "aplicada",
                "data": datetime.now().timestamp()
            }
        }
        test_counter = 3
        
        data_manager.save_punishments(test_punishments, test_counter)
        
        # Carrega novamente
        loaded_punishments, loaded_counter = data_manager.load_punishments()
        
        assert len(loaded_punishments) == 2, "Deveria ter 2 punições"
        assert loaded_counter == 3, "Contador deveria ser 3"
        assert loaded_punishments[1]["quantidade"] == 50, "Quantidade deveria ser 50"
        assert loaded_punishments[2]["status"] == "aplicada", "Status deveria ser aplicada"
        print("Punições salvas e carregadas corretamente")
        
        # Teste 3: Salvar e carregar estados pendentes
        print("\nTeste 3: Salvar e carregar estados pendentes")
        test_pending = {
            123456789: {
                "solicitante": 123456789,
                "punido": 987654321,
                "quantidade": 10,
                "motivo": "Teste pendente",
                "status": "aguardando_foto",
                "canal": 555555555,
                "criado_em": datetime.now().timestamp()
            }
        }
        
        data_manager.save_pending_punishments(test_pending)
        
        # Carrega novamente
        loaded_pending = data_manager.load_pending_punishments()
        
        assert len(loaded_pending) == 1, "Deveria ter 1 estado pendente"
        assert loaded_pending[123456789]["quantidade"] == 10, "Quantidade deveria ser 10"
        assert loaded_pending[123456789]["status"] == "aguardando_foto", "Status deveria ser aguardando_foto"
        print("Estados pendentes salvos e carregados corretamente")
        
        # Teste 4: Backup de punições
        print("\nTeste 4: Backup de punições")
        backup_file = data_manager.backup_punishments()
        
        assert backup_file != "", "Backup deveria retornar um caminho"
        assert os.path.exists(backup_file), "Arquivo de backup deveria existir"
        
        # Verifica o conteúdo do backup
        with open(backup_file, 'r', encoding='utf-8') as f:
            backup_data = json.load(f)
        
        assert "punishments" in backup_data, "Backup deveria conter punições"
        assert "counter" in backup_data, "Backup deveria conter contador"
        assert len(backup_data["punishments"]) == 2, "Backup deveria ter 2 punições"
        print("Backup criado corretamente")
        
        # Teste 5: Estatísticas
        print("\nTeste 5: Estatísticas")
        stats = data_manager.get_statistics()
        
        assert "total_punishments" in stats, "Estatísticas deveriam conter total_punishments"
        assert "total_pending_states" in stats, "Estatísticas deveriam conter total_pending_states"
        assert "next_id" in stats, "Estatísticas deveriam conter next_id"
        assert "status_distribution" in stats, "Estatísticas deveriam conter status_distribution"
        assert "total_jjs_applied" in stats, "Estatísticas deveriam conter total_jjs_applied"
        
        assert stats["total_punishments"] == 2, "Total de punições deveria ser 2"
        assert stats["total_pending_states"] == 1, "Total de estados pendentes deveria ser 1"
        assert stats["next_id"] == 3, "Próximo ID deveria ser 3"
        assert stats["total_jjs_applied"] == 75, "Total de JJ's deveria ser 75"
        print("Estatísticas geradas corretamente")
        
        # Teste 6: Limpar estados pendentes
        print("\nTeste 6: Limpar estados pendentes")
        data_manager.clear_pending_punishments()
        
        # Carrega novamente
        cleared_pending = data_manager.load_pending_punishments()
        
        assert len(cleared_pending) == 0, "Deveria ter 0 estados pendentes após limpeza"
        print("Estados pendentes limpos corretamente")
        
        # Teste 7: Persistência após reinicialização
        print("\nTeste 7: Persistência após reinicialização")
        # Cria um novo gerenciador de dados no mesmo diretório
        new_data_manager = DataManager(temp_dir)
        
        # Carrega os dados
        new_punishments, new_counter = new_data_manager.load_punishments()
        new_pending = new_data_manager.load_pending_punishments()
        
        assert len(new_punishments) == 2, "Novo gerenciador deveria carregar 2 punições"
        assert new_counter == 3, "Novo gerenciador deveria carregar contador 3"
        assert len(new_pending) == 0, "Novo gerenciador deveria carregar 0 estados pendentes"
        print("Dados persistidos corretamente após reinicialização")
        
        print("\nTodos os testes de persistencia passaram!")
        print("=" * 50)


def test_file_structure():
    """
    Testa a estrutura dos arquivos de dados.
    """
    print("\nTestando Estrutura de Arquivos")
    print("=" * 30)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        data_manager = DataManager(temp_dir)
        
        # Verifica se os arquivos são criados
        punishments_file = os.path.join(temp_dir, "punishments.json")
        pending_file = os.path.join(temp_dir, "pending.json")
        
        # Carrega dados para criar os arquivos
        data_manager.load_punishments()
        data_manager.load_pending_punishments()
        
        assert os.path.exists(punishments_file), "Arquivo de punições deveria ser criado"
        assert os.path.exists(pending_file), "Arquivo de estados pendentes deveria ser criado"
        
        # Verifica a estrutura do arquivo de punições
        with open(punishments_file, 'r', encoding='utf-8') as f:
            punishments_data = json.load(f)
        
        assert "punishments" in punishments_data, "Arquivo de punições deveria ter chave 'punishments'"
        assert "counter" in punishments_data, "Arquivo de punições deveria ter chave 'counter'"
        assert isinstance(punishments_data["punishments"], dict), "Punições deveriam ser um dicionário"
        assert isinstance(punishments_data["counter"], int), "Contador deveria ser um inteiro"
        
        # Verifica a estrutura do arquivo de estados pendentes
        with open(pending_file, 'r', encoding='utf-8') as f:
            pending_data = json.load(f)
        
        assert isinstance(pending_data, dict), "Estados pendentes deveriam ser um dicionário"
        
        print("Estrutura de arquivos correta")


def test_error_handling():
    """
    Testa o tratamento de erros do sistema de persistência.
    """
    print("\nTestando Tratamento de Erros")
    print("=" * 30)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        data_manager = DataManager(temp_dir)
        
        # Teste 1: Arquivo corrompido
        print("Teste 1: Arquivo corrompido")
        punishments_file = os.path.join(temp_dir, "punishments.json")
        
        # Cria um arquivo corrompido
        with open(punishments_file, 'w', encoding='utf-8') as f:
            f.write("arquivo corrompido")
        
        # Deve retornar valores padrão
        punishments, counter = data_manager.load_punishments()
        
        assert len(punishments) == 0, "Deveria retornar punições vazias"
        assert counter == 1, "Deveria retornar contador padrão"
        print("Tratamento de arquivo corrompido")
        
        # Teste 2: Diretório inexistente (deve ser criado)
        print("Teste 2: Diretório inexistente")
        non_existent_dir = os.path.join(temp_dir, "novo_diretorio")
        
        new_data_manager = DataManager(non_existent_dir)
        
        assert os.path.exists(non_existent_dir), "Diretório deveria ser criado"
        print("Diretório criado automaticamente")
        
        print("Todos os testes de tratamento de erros passaram!")


if __name__ == "__main__":
    try:
        test_persistence_system()
        test_file_structure()
        test_error_handling()
        
        print("\nTestes de persistencia concluidos com sucesso!")
        print("O sistema de persistencia está funcionando corretamente.")
        
    except Exception as e:
        print(f"\nErro nos testes de persistencia: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)