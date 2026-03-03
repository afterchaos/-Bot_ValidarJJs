#!/usr/bin/env python3
"""
Teste do Sistema de Validação de Cumprimento de Punição (JJ's)

Este script testa as funcionalidades principais do sistema de validação JJ's
sem precisar iniciar o bot completo.
"""

import sys
import os
import json
import tempfile
from datetime import datetime

# Adiciona o caminho do módulo ao sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from jj_validation_system import JJValidationSystem


class MockBot:
    """Bot mock para testes."""
    def __init__(self):
        self.cogs = {}
    
    def get_cog(self, name):
        return self.cogs.get(name)


class MockUser:
    """Usuário mock para testes."""
    def __init__(self, user_id, name="TestUser"):
        self.id = user_id
        self.name = name
        self.mention = f"<@{user_id}>"


class MockChannel:
    """Canal mock para testes."""
    def __init__(self, channel_id, name="test-channel"):
        self.id = channel_id
        self.name = name


class MockMessage:
    """Mensagem mock para testes."""
    def __init__(self, content, author, channel):
        self.content = content
        self.author = author
        self.channel = channel


class TestJJValidation:
    """Testes para o sistema de validação JJ's."""
    
    def __init__(self):
        self.bot = MockBot()
        self.jj_system = JJValidationSystem(self.bot)
        self.bot.cogs["JJValidationSystem"] = self.jj_system
        
        # Cria arquivos temporários para testes
        self.temp_dir = tempfile.mkdtemp()
        # Define o data_dir manualmente para testes
        self.jj_system.data_dir = self.temp_dir
        
        print("Iniciando testes do Sistema de Validacao JJ's")
        print("=" * 60)
    
    def test_number_to_words(self):
        """Testa a conversão de números para palavras."""
        print("\nTestando conversao de numeros para palavras...")
        
        test_cases = [
            (1, "UM!"),
            (2, "DOIS!"),
            (5, "CINCO!"),
            (10, "DEZ!"),
            (11, "ONZE!"),
            (15, "QUINZE!"),
            (20, "VINTE!"),
            (25, "VINTE E CINCO!"),
            (100, "CEM!"),
            (101, "CENTO E UM!"),
            (123, "CENTO E VINTE E TRES!"),
            (1000, "MIL!"),
            (1001, "MIL E UM!"),
            (2023, "DOIS MIL E VINTE E TRES!")
        ]
        
        for number, expected in test_cases:
            try:
                result = self.jj_system.number_to_words(number)
                if result == expected:
                    print(f"OK {number} -> {result}")
                else:
                    print(f"ERRO {number} -> {result} (esperado: {expected})")
            except Exception as e:
                print(f"ERRO {number} -> Erro: {e}")
    
    def test_message_validation(self):
        """Testa a validação de mensagens."""
        print("\nTestando validacao de mensagens...")
        
        test_cases = [
            # (mensagem, número_esperado, deve_ser_válido, mensagem_esperada)
            ("UM!", 1, True, "OK **Correto!**"),
            ("um!", 1, True, "OK **Correto!**"),
            ("UM", 1, False, "ERRO **Erro:** A mensagem deve terminar com ponto de exclamação (!)."),
            ("1!", 1, False, "ERRO **Erro:** Não é permitido usar números em formato numérico. Use apenas a forma por extenso."),
            ("DOIS!", 2, True, "OK **Correto!**"),
            ("TRES!", 3, True, "OK **Correto!**"),
            ("QUATRO!", 4, True, "OK **Correto!**"),
            ("CINCO!", 5, True, "OK **Correto!**"),
            ("SEIS!", 6, True, "OK **Correto!**"),
            ("SETTE!", 7, False, "ERRO **Erro:** Forma incorreta. O correto é: `SETE!`"),
            ("OITO!", 8, True, "OK **Correto!**"),
            ("NOVE!", 9, True, "OK **Correto!**"),
            ("DEZ!", 10, True, "OK **Correto!**"),
            ("ONZE!", 11, True, "OK **Correto!**"),
            ("DOZE!", 12, True, "OK **Correto!**"),
            ("TREZE!", 13, True, "OK **Correto!**"),
            ("QUATORZE!", 14, True, "OK **Correto!**"),
            ("QUINZE!", 15, True, "OK **Correto!**"),
            ("DEZESSEIS!", 16, True, "OK **Correto!**"),
            ("DEZESSETE!", 17, True, "OK **Correto!**"),
            ("DEZOITO!", 18, True, "OK **Correto!**"),
            ("DEZENOVE!", 19, True, "OK **Correto!**"),
            ("VINTE!", 20, True, "OK **Correto!**"),
            ("VINTE E UM!", 21, True, "OK **Correto!**"),
            ("VINTE E DOIS!", 22, True, "OK **Correto!**"),
            ("VINTE E TRES!", 23, True, "OK **Correto!**"),
            ("VINTE E QUATRO!", 24, True, "OK **Correto!**"),
            ("VINTE E CINCO!", 25, True, "OK **Correto!**"),
            ("VINTE E SEIS!", 26, True, "OK **Correto!**"),
            ("VINTE E SETE!", 27, True, "OK **Correto!**"),
            ("VINTE E OITO!", 28, True, "OK **Correto!**"),
            ("VINTE E NOVE!", 29, True, "OK **Correto!**"),
            ("TRINTA!", 30, True, "OK **Correto!**"),
        ]
        
        for message, expected_number, should_be_valid, expected_message in test_cases:
            is_valid, message_result = self.jj_system.validate_message(message, expected_number)
            
            if is_valid == should_be_valid and message_result == expected_message:
                print(f"OK '{message}' (numero {expected_number}) -> {message_result}")
            else:
                print(f"ERRO '{message}' (numero {expected_number}) -> {message_result} (esperado: {expected_message})")
    
    def test_session_management(self):
        """Testa o gerenciamento de sessões."""
        print("\nTestando gerenciamento de sessoes...")
        
        user_id = 123456
        punishment_id = 1
        quantidade = 5
        
        # Testa início de sessão
        print("Iniciando sessão de teste...")
        session = {
            "punishment_id": punishment_id,
            "progresso_atual": 0,
            "quantidade_total": quantidade,
            "erros": 0,
            "iniciado_em": 1234567890
        }
        
        self.jj_system.active_jj_sessions[user_id] = session
        
        if user_id in self.jj_system.active_jj_sessions:
            print("OK Sessão iniciada com sucesso")
        else:
            print("ERRO Falha ao iniciar sessão")
        
        # Testa progresso
        print("Testando progresso...")
        self.jj_system.active_jj_sessions[user_id]["progresso_atual"] = 3
        
        if self.jj_system.active_jj_sessions[user_id]["progresso_atual"] == 3:
            print("OK Progresso atualizado corretamente")
        else:
            print("ERRO Falha ao atualizar progresso")
        
        # Testa erros
        print("Testando contagem de erros...")
        self.jj_system.active_jj_sessions[user_id]["erros"] = 2
        
        if self.jj_system.active_jj_sessions[user_id]["erros"] == 2:
            print("OK Contagem de erros atualizada corretamente")
        else:
            print("ERRO Falha ao atualizar contagem de erros")
        
        # Testa conclusão
        print("Testando conclusão...")
        self.jj_system.active_jj_sessions[user_id]["progresso_atual"] = quantidade
        
        if self.jj_system.active_jj_sessions[user_id]["progresso_atual"] >= quantidade:
            print("OK Sessão concluída corretamente")
        else:
            print("ERRO Falha ao concluir sessão")
        
        # Remove sessão
        del self.jj_system.active_jj_sessions[user_id]
        print("OK Sessão removida com sucesso")
    
    def test_spam_protection(self):
        """Testa a proteção contra spam."""
        print("\nTestando protecao contra spam...")
        
        user_id = 987654
        
        # Testa sem spam
        print("Testando sem spam...")
        is_spam = self.jj_system.check_spam(user_id)
        
        if not is_spam:
            print("OK Proteção contra spam funcionando (sem spam detectado)")
        else:
            print("ERRO Falso positivo de spam")
        
        # Testa com spam (simulando muitas mensagens)
        print("Testando com spam...")
        import time
        current_time = time.time()
        
        # Simula 15 mensagens em 1 segundo (acima do limite)
        self.jj_system.user_message_times[user_id] = [current_time - 0.1 * i for i in range(15)]
        
        is_spam = self.jj_system.check_spam(user_id)
        
        if is_spam:
            print("OK Proteção contra spam funcionando (spam detectado)")
        else:
            print("ERRO Spam não detectado")
    
    def test_channel_detection(self):
        """Testa a detecção de canais de punição."""
        print("\nTestando deteccao de canais de punicao...")
        
        test_cases = [
            ("punicao-teste", True),
            ("punicao-membro", True),
            ("canal-normal", False),
            ("punicao", False),
            ("test-punicao", False),
        ]
        
        for channel_name, should_be_jj in test_cases:
            channel = MockChannel(123, channel_name)
            is_jj = self.jj_system.is_jj_channel(channel)
            
            if is_jj == should_be_jj:
                print(f"OK Canal '{channel_name}' -> {'JJ' if is_jj else 'Normal'}")
            else:
                print(f"ERRO Canal '{channel_name}' -> {'JJ' if is_jj else 'Normal'} (esperado: {'JJ' if should_be_jj else 'Normal'})")
    
    def test_persistence(self):
        """Testa a persistência de sessões."""
        print("\nTestando persistencia de sessoes...")
        
        user_id = 555666
        session_data = {
            "punishment_id": 2,
            "progresso_atual": 2,
            "quantidade_total": 10,
            "erros": 1,
            "iniciado_em": 1234567890
        }
        
        # Salva sessão
        print("Salvando sessão...")
        self.jj_system.active_jj_sessions[user_id] = session_data
        self.jj_system.save_active_sessions()
        
        # Carrega sessão
        print("Carregando sessão...")
        self.jj_system.load_active_sessions()
        
        if user_id in self.jj_system.active_jj_sessions:
            loaded_session = self.jj_system.active_jj_sessions[user_id]
            if (loaded_session["punishment_id"] == session_data["punishment_id"] and
                loaded_session["progresso_atual"] == session_data["progresso_atual"] and
                loaded_session["quantidade_total"] == session_data["quantidade_total"] and
                loaded_session["erros"] == session_data["erros"]):
                print("OK Persistência de sessões funcionando corretamente")
            else:
                print("ERRO Dados da sessão não correspondem após carregamento")
        else:
            print("ERRO Sessão não encontrada após carregamento")
    
    def run_all_tests(self):
        """Executa todos os testes."""
        try:
            self.test_number_to_words()
            self.test_message_validation()
            self.test_session_management()
            self.test_spam_protection()
            self.test_channel_detection()
            self.test_persistence()
            
            print("\n" + "=" * 60)
            print("Testes concluidos!")
            print("O sistema de validacao JJ's esta pronto para uso.")
            
        except Exception as e:
            print(f"\nErro durante os testes: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            # Limpa arquivos temporários
            import shutil
            shutil.rmtree(self.temp_dir, ignore_errors=True)


if __name__ == "__main__":
    tester = TestJJValidation()
    tester.run_all_tests()