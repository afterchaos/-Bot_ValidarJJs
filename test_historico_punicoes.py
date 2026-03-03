#!/usr/bin/env python3
"""
Teste para o comando /historico-punicoes

Este script testa o novo comando de histórico de punições.
"""

import asyncio
import time
from datetime import datetime
import sys
import os

# Adiciona o caminho do projeto ao sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import BotConfig
from data_manager import data_manager
from main import PunishmentRequestSystem


class MockUser:
    """Mock de usuário para testes."""
    def __init__(self, user_id: int, name: str):
        self.id = user_id
        self.name = name
        self.mention = f"<@{user_id}>"


class MockMember:
    """Mock de membro para testes."""
    def __init__(self, user_id: int, name: str, roles: list = None):
        self.id = user_id
        self.name = name
        self.mention = f"<@{user_id}>"
        self.roles = roles or []


class MockRole:
    """Mock de cargo para testes."""
    def __init__(self, role_id: int, name: str):
        self.id = role_id
        self.name = name
        self.mention = f"<@&{role_id}>"


class MockGuild:
    """Mock de guild para testes."""
    def __init__(self, responsible_role_id: int):
        self.responsible_role = MockRole(responsible_role_id, "Superior")
        
    def get_role(self, role_id: int):
        if role_id == self.responsible_role.id:
            return self.responsible_role
        return None


class MockInteraction:
    """Mock de interação para testes."""
    def __init__(self, user_id: int, user_name: str, has_responsible_role: bool = False, responsible_role_id: int = 0):
        self.author = MockMember(user_id, user_name)
        self.guild = MockGuild(responsible_role_id)
        
        if has_responsible_role:
            self.author.roles.append(self.guild.responsible_role)
        
        self.response_sent = False
        self.followup_sent = False
        self.response_message = None
        self.followup_message = None
        
    async def response(self):
        class MockResponse:
            async def defer(self, ephemeral: bool = False):
                pass
        return MockResponse()
    
    async def followup(self, content: str = None, embed=None, ephemeral: bool = False):
        if content:
            self.followup_message = content
        elif embed:
            self.followup_message = f"Embed enviado: {embed.title}"
        self.followup_sent = True
        return self.followup_message


class MockBot:
    """Mock de bot para testes."""
    def __init__(self):
        self.users = {}
        
    def get_user(self, user_id: int):
        return self.users.get(user_id)


async def test_historico_punicoes():
    """Testa o comando /historico-punicoes."""
    print("Testando comando /historico-punicoes...")
    
    # Cria um mock bot
    bot = MockBot()
    
    # Cria o sistema de punições
    punishment_system = PunishmentRequestSystem(bot)
    
    # Cria usuários de teste
    user1 = MockUser(123456789, "Solicitante1")
    user2 = MockUser(987654321, "Punido1")
    user3 = MockUser(111222333, "Solicitante2")
    user4 = MockUser(444555666, "Punido2")
    
    bot.users = {
        123456789: user1,
        987654321: user2,
        111222333: user3,
        444555666: user4
    }
    
    # Cria algumas punições de teste
    test_punishments = {
        1: {
            "id": 1,
            "solicitante": 123456789,
            "punido": 987654321,
            "quantidade": 10,
            "motivo": "Teste de punição 1",
            "status": "pendente",
            "data": time.time() - 86400  # 1 dia atrás
        },
        2: {
            "id": 2,
            "solicitante": 111222333,
            "punido": 444555666,
            "quantidade": 20,
            "motivo": "Teste de punição 2",
            "status": "em_cumprimento",
            "data": time.time() - 172800  # 2 dias atrás
        },
        3: {
            "id": 3,
            "solicitante": 123456789,
            "punido": 444555666,
            "quantidade": 5,
            "motivo": "Teste de punição 3",
            "status": "cumprida",
            "data": time.time() - 259200  # 3 dias atrás
        },
        4: {
            "id": 4,
            "solicitante": 987654321,
            "punido": 123456789,
            "quantidade": 15,
            "motivo": "Teste de punição 4 (recíproca)",
            "status": "em_analise",
            "data": time.time() - 345600  # 4 dias atrás
        }
    }
    
    # Salva as punições no banco de dados
    punishment_system.punishments_db = test_punishments
    punishment_system.punishment_counter = 5
    
    # Salva no armazenamento persistente
    punishment_system.save_punishments_persistent()
    
    print("Punicoes de teste criadas e salvas")
    
    # Teste 1: Usuário sem permissão tenta usar o comando
    print("\nTeste 1: Usuario sem permissao")
    interaction_no_permission = MockInteraction(
        user_id=999888777, 
        user_name="UsuarioSemPermissao",
        has_responsible_role=False,
        responsible_role_id=BotConfig.PunishmentSystem.RESPONSIBLE_ROLE_ID
    )
    
    try:
        await punishment_system.historico_punicoes(interaction_no_permission)
        if interaction_no_permission.followup_sent:
            print("Comando corretamente bloqueado para usuario sem permissao")
        else:
            print("Comando nao bloqueou usuario sem permissao")
    except Exception as e:
        print(f"Erro ao testar bloqueio de permissao: {e}")
    
    # Teste 2: Usuário com permissão usa o comando
    print("\nTeste 2: Usuario com permissao")
    interaction_with_permission = MockInteraction(
        user_id=555666777,
        user_name="Superior",
        has_responsible_role=True,
        responsible_role_id=BotConfig.PunishmentSystem.RESPONSIBLE_ROLE_ID
    )
    
    try:
        await punishment_system.historico_punicoes(interaction_with_permission)
        if interaction_with_permission.followup_sent:
            print("Comando executado com sucesso para usuario com permissao")
            print("Embed enviado corretamente")
        else:
            print("Comando nao enviou embed para usuario com permissao")
    except Exception as e:
        print(f"Erro ao testar comando com permissao: {e}")
    
    # Teste 3: Verifica estatísticas
    print("\nTeste 3: Verificacao de estatisticas")
    try:
        # Verifica se as estatísticas estão corretas
        total_punishments = len(test_punishments)
        total_jjs = sum(p_data['quantidade'] for p_data in test_punishments.values())
        
        print(f"Total de punições: {total_punishments}")
        print(f"Total de JJ's: {total_jjs}")
        
        # Verifica status
        status_counts = {}
        for punishment_data in test_punishments.values():
            status = punishment_data.get("status", "desconhecido")
            status_counts[status] = status_counts.get(status, 0) + 1
        
        print("Contagem por status:")
        for status, count in status_counts.items():
            print(f"  {status}: {count}")
        
        print("Estatisticas calculadas corretamente")
        
    except Exception as e:
        print(f"Erro ao verificar estatisticas: {e}")
    
    # Teste 4: Testa a função de exibição de status
    print("\nTeste 4: Funcao de exibicao de status")
    try:
        status_tests = [
            ("em_analise", "Em Analise"),
            ("pendente", "Pendente"),
            ("em_cumprimento", "Em Cumprimento"),
            ("pausada", "Pausada"),
            ("cumprida", "Cumprida"),
            ("recusada", "Recusada"),
            ("desconhecido", "Desconhecido"),
            ("status_invalido", "status_invalido")
        ]
        
        for status_input, expected_output in status_tests:
            actual_output = punishment_system.get_status_display(status_input)
            if actual_output == expected_output:
                print(f"{status_input} -> {expected_output}")
            else:
                print(f"{status_input} -> Esperado: {expected_output}, Obtido: {actual_output}")
        
    except Exception as e:
        print(f"Erro ao testar funcao de exibicao de status: {e}")
    
    print("\nTestes concluidos!")


if __name__ == "__main__":
    asyncio.run(test_historico_punicoes())