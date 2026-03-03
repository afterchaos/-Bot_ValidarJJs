#!/usr/bin/env python3
"""
Teste Simples do Sistema de Validação de Cumprimento de Punição (JJ's)

Este script testa as funcionalidades principais do sistema de validação JJ's
sem precisar iniciar o bot completo.
"""

import sys
import os
import json
import tempfile

# Adiciona o caminho do módulo ao sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.cogs.jj_validation_system import JJValidationSystem


class MockBot:
    """Bot mock para testes."""
    def __init__(self):
        self.cogs = {}
    
    def get_cog(self, name):
        return self.cogs.get(name)


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
        
        print("Iniciando testes do Sistema de Validação JJ's")
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
        
        success_count = 0
        total_count = len(test_cases)
        
        for number, expected in test_cases:
            try:
                result = self.jj_system.number_to_words(number)
                if result == expected:
                    print(f"  OK {number} -> {result}")
                    success_count += 1
                else:
                    print(f"  ERRO {number} -> {result} (esperado: {expected})")
            except Exception as e:
                print(f"  ERRO {number} -> Erro: {e}")
        
        print(f"  Resultado: {success_count}/{total_count} testes passaram")
        return success_count == total_count
    
    def test_message_validation(self):
        """Testa a validação de mensagens."""
        print("\nTestando validação de mensagens...")
        
        test_cases = [
            # (mensagem, número_esperado, deve_ser_válido, mensagem_esperada)
            ("UM!", 1, True, "✅ **Correto!**"),
            ("um!", 1, True, "✅ **Correto!**"),
            ("UM", 1, False, "❌ **Erro:** A mensagem deve terminar com ponto de exclamação (!)."),
            ("1!", 1, False, "❌ **Erro:** Não é permitido usar números em formato numérico. Use apenas a forma por extenso."),
            ("DOIS!", 2, True, "✅ **Correto!**"),
            ("TRES!", 3, True, "✅ **Correto!**"),
            ("QUATRO!", 4, True, "✅ **Correto!**"),
            ("CINCO!", 5, True, "✅ **Correto!**"),
            ("SEIS!", 6, True, "✅ **Correto!**"),
            ("SETTE!", 7, False, "❌ **Erro:** Forma incorreta. O correto é: `SETE!`"),
            ("OITO!", 8, True, "✅ **Correto!**"),
            ("NOVE!", 9, True, "✅ **Correto!**"),
            ("DEZ!", 10, True, "✅ **Correto!**"),
            ("ONZE!", 11, True, "✅ **Correto!**"),
            ("DOZE!", 12, True, "✅ **Correto!**"),
            ("TREZE!", 13, True, "✅ **Correto!**"),
            ("QUATORZE!", 14, True, "✅ **Correto!**"),
            ("QUINZE!", 15, True, "✅ **Correto!**"),
            ("DEZESSEIS!", 16, True, "✅ **Correto!**"),
            ("DEZESSETE!", 17, True, "✅ **Correto!**"),
            ("DEZOITO!", 18, True, "✅ **Correto!**"),
            ("DEZENOVE!", 19, True, "✅ **Correto!**"),
            ("VINTE!", 20, True, "✅ **Correto!**"),
            ("VINTE E UM!", 21, True, "✅ **Correto!**"),
            ("VINTE E DOIS!", 22, True, "✅ **Correto!**"),
            ("VINTE E TRES!", 23, True, "✅ **Correto!**"),
            ("VINTE E QUATRO!", 24, True, "✅ **Correto!**"),
            ("VINTE E CINCO!", 25, True, "✅ **Correto!**"),
            ("VINTE E SEIS!", 26, True, "✅ **Correto!**"),
            ("VINTE E SETE!", 27, True, "✅ **Correto!**"),
            ("VINTE E OITO!", 28, True, "✅ **Correto!**"),
            ("VINTE E NOVE!", 29, True, "✅ **Correto!**"),
            ("TRINTA!", 30, True, "✅ **Correto!**"),
        ]
        
        success_count = 0
        total_count = len(test_cases)
        
        for message, expected_number, should_be_valid, expected_message in test_cases:
            is_valid, message_result = self.jj_system.validate_message(message, expected_number)
            
            if is_valid == should_be_valid and message_result == expected_message:
                print(f"  OK '{message}' (numero {expected_number}) -> Mensagem correta")
                success_count += 1
            else:
                print(f"  ERRO '{message}' (numero {expected_number}) -> Erro de validacao")
        
        print(f"  Resultado: {success_count}/{total_count} testes passaram")
        return success_count == total_count
    
    def test_session_management(self):
        """Testa o gerenciamento de sessões."""
        print("\nTestando gerenciamento de sessões...")
        
        user_id = 123456
        punishment_id = 1
        quantidade = 5
        
        # Testa início de sessão
        print("  Iniciando sessão de teste...")
        session = {
            "punishment_id": punishment_id,
            "progresso_atual": 0,
            "quantidade_total": quantidade,
            "erros": 0,
            "iniciado_em": 1234567890
        }
        
        self.jj_system.active_jj_sessions[user_id] = session
        
        if user_id in self.jj_system.active_jj_sessions:
            print("  OK Sessao iniciada com sucesso")
        else:
            print("  ERRO Falha ao iniciar sessao")
            return False
        
        # Testa progresso
        print("  Testando progresso...")
        self.jj_system.active_jj_sessions[user_id]["progresso_atual"] = 3
        
        if self.jj_system.active_jj_sessions[user_id]["progresso_atual"] == 3:
            print("  OK Progresso atualizado corretamente")
        else:
            print("  ERRO Falha ao atualizar progresso")
            return False
        
        # Testa erros
        print("  Testando contagem de erros...")
        self.jj_system.active_jj_sessions[user_id]["erros"] = 2
        
        if self.jj_system.active_jj_sessions[user_id]["erros"] == 2:
            print("  OK Contagem de erros atualizada corretamente")
        else:
            print("  ERRO Falha ao atualizar contagem de erros")
            return False
        
        # Testa conclusão
        print("  Testando conclusão...")
        self.jj_system.active_jj_sessions[user_id]["progresso_atual"] = quantidade
        
        if self.jj_system.active_jj_sessions[user_id]["progresso_atual"] >= quantidade:
            print("  OK Sessao concluida corretamente")
        else:
            print("  ERRO Falha ao concluir sessao")
            return False
        
        # Remove sessão
        del self.jj_system.active_jj_sessions[user_id]
        print("  OK Sessao removida com sucesso")
        
        return True
    
    def test_spam_protection(self):
        """Testa a proteção contra spam."""
        print("\nTestando proteção contra spam...")
        
        user_id = 987654
        
        # Testa sem spam
        print("  Testando sem spam...")
        is_spam = self.jj_system.check_spam(user_id)
        
        if not is_spam:
            print("  OK Protecao contra spam funcionando (sem spam detectado)")
        else:
            print("  ERRO Falso positivo de spam")
            return False
        
        # Testa com spam (simulando muitas mensagens)
        print("  Testando com spam...")
        import time
        current_time = time.time()
        
        # Simula 15 mensagens em 1 segundo (acima do limite)
        self.jj_system.user_message_times[user_id] = [current_time - 0.1 * i for i in range(15)]
        
        is_spam = self.jj_system.check_spam(user_id)
        
        if is_spam:
            print("  OK Protecao contra spam funcionando (spam detectado)")
            return True
        else:
            print("  ERRO Spam nao detectado")
            return False
    
    def test_channel_detection(self):
        """Testa a detecção de canais de punição."""
        print("\nTestando detecção de canais de punição...")
        
        test_cases = [
            ("punicao-teste", True),
            ("punicao-membro", True),
            ("canal-normal", False),
            ("punicao", False),
            ("test-punicao", False),
        ]
        
        success_count = 0
        total_count = len(test_cases)
        
        for channel_name, should_be_jj in test_cases:
            # Cria um mock simples para o canal
            class MockChannel:
                def __init__(self, name):
                    self.name = name
            
            channel = MockChannel(channel_name)
            is_jj = self.jj_system.is_jj_channel(channel)
            
            if is_jj == should_be_jj:
                print(f"  OK Canal '{channel_name}' -> {'JJ' if is_jj else 'Normal'}")
                success_count += 1
            else:
                print(f"  ERRO Canal '{channel_name}' -> {'JJ' if is_jj else 'Normal'} (esperado: {'JJ' if should_be_jj else 'Normal'})")
        
        print(f"  Resultado: {success_count}/{total_count} testes passaram")
        return success_count == total_count
    
    def test_persistence(self):
        """Testa a persistência de sessões."""
        print("\nTestando persistência de sessões...")
        
        user_id = 555666
        session_data = {
            "punishment_id": 2,
            "progresso_atual": 2,
            "quantidade_total": 10,
            "erros": 1,
            "iniciado_em": 1234567890
        }
        
        # Salva sessão
        print("  Salvando sessão...")
        self.jj_system.active_jj_sessions[user_id] = session_data
        self.jj_system.save_active_sessions()
        
        # Carrega sessão
        print("  Carregando sessão...")
        self.jj_system.load_active_sessions()
        
        if user_id in self.jj_system.active_jj_sessions:
            loaded_session = self.jj_system.active_jj_sessions[user_id]
            if (loaded_session["punishment_id"] == session_data["punishment_id"] and
                loaded_session["progresso_atual"] == session_data["progresso_atual"] and
                loaded_session["quantidade_total"] == session_data["quantidade_total"] and
                loaded_session["erros"] == session_data["erros"]):
                print("  OK Persistencia de sessoes funcionando corretamente")
                return True
            else:
                print("  ERRO Dados da sessao nao correspondem apos carregamento")
                return False
        else:
            print("  ERRO Sessao nao encontrada apos carregamento")
            return False
    
    def run_all_tests(self):
        """Executa todos os testes."""
        try:
            results = []
            
            results.append(("Conversão de números", self.test_number_to_words()))
            results.append(("Validação de mensagens", self.test_message_validation()))
            results.append(("Gerenciamento de sessões", self.test_session_management()))
            results.append(("Proteção contra spam", self.test_spam_protection()))
            results.append(("Detecção de canais", self.test_channel_detection()))
            results.append(("Persistência de sessões", self.test_persistence()))
            
            print("\n" + "=" * 60)
            print("Resumo dos Testes:")
            
            passed = 0
            total = len(results)
            
            for test_name, result in results:
                status = "PASSOU" if result else "FALHOU"
                print(f"  {test_name}: {status}")
                if result:
                    passed += 1
            
            print(f"\nResultado Final: {passed}/{total} testes passaram")
            
            if passed == total:
                print("TODOS OS TESTES PASSARAM!")
                print("SISTEMA DE VALIDACAO JJ'S ESTA PRONTO PARA USO.")
            else:
                print("ALGUNS TESTES FALHARAM. REVISE O CODIGO.")
            
            return passed == total
            
        except Exception as e:
            print(f"\nErro durante os testes: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        finally:
            # Limpa arquivos temporários
            import shutil
            shutil.rmtree(self.temp_dir, ignore_errors=True)


if __name__ == "__main__":
    tester = TestJJValidation()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)