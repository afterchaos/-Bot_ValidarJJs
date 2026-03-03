#!/usr/bin/env python3
"""
Teste para validar a funcionalidade de permissões separadas para o comando /limpar-punicoes.

Este teste verifica se o comando /limpar-punicoes agora usa uma validação de cargos separada
dos demais comandos de punição, permitindo que apenas membros com cargos específicos
possam limpar o histórico de punições.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Adiciona o caminho do projeto para importar os módulos
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.utils.config import BotConfig
from src.main import PunishmentRequestSystem


class TestClearPunishmentsRoles(unittest.TestCase):
    """Testes para validação de permissões do comando /limpar-punicoes."""
    
    def setUp(self):
        """Configura o ambiente de teste."""
        # Cria um mock do bot
        self.bot = Mock()
        self.bot.get_user = Mock()
        
        # Cria uma instância do sistema de punição
        self.punishment_system = PunishmentRequestSystem(self.bot)
        
        # Mock de membro com cargos
        self.member_with_clear_role = Mock()
        self.member_with_clear_role.id = 123456789
        self.member_with_clear_role.guild = Mock()
        self.member_with_clear_role.mention = "<@123456789>"
        
        # Mock de membro sem cargo de limpeza
        self.member_without_clear_role = Mock()
        self.member_without_clear_role.id = 987654321
        self.member_without_clear_role.guild = Mock()
        self.member_without_clear_role.mention = "<@987654321>"
        
        # Mock de membro com cargo permitido (mas não de limpeza)
        self.member_with_allowed_role = Mock()
        self.member_with_allowed_role.id = 555666777
        self.member_with_allowed_role.guild = Mock()
        self.member_with_allowed_role.mention = "<@555666777>"
    
    def test_validate_clear_punishments_permissions_with_configured_roles(self):
        """Testa a validação de permissões para /limpar-punicoes com cargos configurados."""
        # Configura os cargos de limpeza no config
        BotConfig.PunishmentSystem.CLEAR_PUNISHMENTS_ROLE_IDS = [111111111, 222222222]
        
        # Mock de cargo de limpeza
        clear_role = Mock()
        clear_role.id = 111111111
        clear_role.mention = "<@&111111111>"
        
        # Mock de cargo permitido (não de limpeza)
        allowed_role = Mock()
        allowed_role.id = 333333333
        allowed_role.mention = "<@&333333333>"
        
        # Configura os membros com cargos
        self.member_with_clear_role.roles = [clear_role]
        self.member_without_clear_role.roles = [allowed_role]
        self.member_with_allowed_role.roles = [allowed_role]
        
        # Testa membro com cargo de limpeza
        has_permission, message = self.punishment_system.validate_clear_punishments_permissions(
            self.member_with_clear_role
        )
        self.assertTrue(has_permission, "Membro com cargo de limpeza deve ter permissão")
        self.assertEqual(message, "Permissão concedida")
        
        # Testa membro sem cargo de limpeza
        has_permission, message = self.punishment_system.validate_clear_punishments_permissions(
            self.member_without_clear_role
        )
        self.assertFalse(has_permission, "Membro sem cargo de limpeza não deve ter permissão")
        self.assertIn("Acesso Negado", message)
        self.assertIn("cargos de limpeza configurados", message)
        
        # Testa membro com cargo permitido (mas não de limpeza)
        has_permission, message = self.punishment_system.validate_clear_punishments_permissions(
            self.member_with_allowed_role
        )
        self.assertFalse(has_permission, "Membro com cargo permitido (mas não de limpeza) não deve ter permissão")
        self.assertIn("Acesso Negado", message)
        self.assertIn("cargos de limpeza configurados", message)
    
    def test_validate_clear_punishments_permissions_without_configured_roles(self):
        """Testa a validação de permissões para /limpar-punicoes sem cargos configurados."""
        # Remove os cargos de limpeza do config
        BotConfig.PunishmentSystem.CLEAR_PUNISHMENTS_ROLE_IDS = []
        
        # Testa membro com qualquer cargo
        has_permission, message = self.punishment_system.validate_clear_punishments_permissions(
            self.member_with_clear_role
        )
        self.assertTrue(has_permission, "Sem cargos configurados, qualquer membro deve ter permissão")
        self.assertEqual(message, "Permissão concedida (nenhum cargo de limpeza configurado)")
        
        # Testa membro sem cargo
        has_permission, message = self.punishment_system.validate_clear_punishments_permissions(
            self.member_without_clear_role
        )
        self.assertTrue(has_permission, "Sem cargos configurados, qualquer membro deve ter permissão")
        self.assertEqual(message, "Permissão concedida (nenhum cargo de limpeza configurado)")
    
    def test_validate_clear_punishments_permissions_with_multiple_roles(self):
        """Testa a validação de permissões para /limpar-punicoes com múltiplos cargos."""
        # Configura múltiplos cargos de limpeza
        BotConfig.PunishmentSystem.CLEAR_PUNISHMENTS_ROLE_IDS = [111111111, 222222222, 333333333]
        
        # Mock de cargos
        role1 = Mock()
        role1.id = 111111111
        role1.mention = "<@&111111111>"
        
        role2 = Mock()
        role2.id = 222222222
        role2.mention = "<@&222222222>"
        
        role3 = Mock()
        role3.id = 333333333
        role3.mention = "<@&333333333>"
        
        # Testa membro com um dos cargos de limpeza
        self.member_with_clear_role.roles = [role1]
        has_permission, message = self.punishment_system.validate_clear_punishments_permissions(
            self.member_with_clear_role
        )
        self.assertTrue(has_permission, "Membro com um dos cargos de limpeza deve ter permissão")
        self.assertEqual(message, "Permissão concedida")
        
        # Testa membro com múltiplos cargos (um deles de limpeza)
        self.member_with_clear_role.roles = [role1, role2, role3]
        has_permission, message = self.punishment_system.validate_clear_punishments_permissions(
            self.member_with_clear_role
        )
        self.assertTrue(has_permission, "Membro com múltiplos cargos (incluindo de limpeza) deve ter permissão")
        self.assertEqual(message, "Permissão concedida")
        
        # Testa membro sem nenhum cargo de limpeza
        other_role = Mock()
        other_role.id = 999999999
        other_role.mention = "<@&999999999>"
        
        self.member_without_clear_role.roles = [other_role]
        has_permission, message = self.punishment_system.validate_clear_punishments_permissions(
            self.member_without_clear_role
        )
        self.assertFalse(has_permission, "Membro sem cargo de limpeza não deve ter permissão")
        self.assertIn("Acesso Negado", message)
        self.assertIn("cargos de limpeza configurados", message)
    
    def test_validate_clear_punishments_permissions_with_invalid_role_ids(self):
        """Testa a validação de permissões para /limpar-punicoes com IDs de cargo inválidos."""
        # Configura cargos de limpeza com IDs inválidos
        BotConfig.PunishmentSystem.CLEAR_PUNISHMENTS_ROLE_IDS = [111111111, 222222222]
        
        # Mock de cargo que não existe no servidor
        invalid_role = Mock()
        invalid_role.id = 999999999
        invalid_role.mention = "<@&999999999>"
        
        # Configura membro com cargo inválido
        self.member_without_clear_role.roles = [invalid_role]
        
        has_permission, message = self.punishment_system.validate_clear_punishments_permissions(
            self.member_without_clear_role
        )
        self.assertFalse(has_permission, "Membro com cargo inválido não deve ter permissão")
        self.assertIn("Acesso Negado", message)
        self.assertIn("cargos de limpeza configurados", message)
    
    def test_validate_clear_punishments_permissions_message_format(self):
        """Testa o formato da mensagem de erro para permissões negadas."""
        # Configura cargos de limpeza
        BotConfig.PunishmentSystem.CLEAR_PUNISHMENTS_ROLE_IDS = [111111111, 222222222]
        
        # Mock de cargos
        role1 = Mock()
        role1.id = 111111111
        role1.mention = "<@&111111111>"
        
        role2 = Mock()
        role2.id = 222222222
        role2.mention = "<@&222222222>"
        
        # Configura membro sem cargo de limpeza
        other_role = Mock()
        other_role.id = 999999999
        other_role.mention = "<@&999999999>"
        
        self.member_without_clear_role.roles = [other_role]
        
        has_permission, message = self.punishment_system.validate_clear_punishments_permissions(
            self.member_without_clear_role
        )
        
        self.assertFalse(has_permission)
        self.assertIn("❌ **Acesso Negado!**", message)
        self.assertIn("Apenas membros com um dos seguintes cargos podem usar este comando:", message)
        self.assertIn("cargos de limpeza configurados", message)
    
    def test_clear_punishments_command_uses_correct_validation(self):
        """Testa se o comando /limpar-punicoes usa a validação correta de cargos de limpeza."""
        # Verifica se o método de validação de limpeza existe
        self.assertTrue(hasattr(self.punishment_system, 'validate_clear_punishments_permissions'),
                       "O método validate_clear_punishments_permissions deve existir")
        
        # Verifica se o método é diferente do método de validação geral
        self.assertNotEqual(self.punishment_system.validate_user_permissions,
                          self.punishment_system.validate_clear_punishments_permissions,
                          "Os métodos de validação devem ser diferentes")
        
        # Testa que ambos os métodos existem e são chamáveis
        self.assertTrue(callable(self.punishment_system.validate_user_permissions),
                       "validate_user_permissions deve ser chamável")
        self.assertTrue(callable(self.punishment_system.validate_clear_punishments_permissions),
                       "validate_clear_punishments_permissions deve ser chamável")


if __name__ == '__main__':
    # Configura o logging para não poluir os testes
    import logging
    logging.disable(logging.CRITICAL)
    
    # Executa os testes
    unittest.main(verbosity=2)