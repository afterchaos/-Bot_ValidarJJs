#!/usr/bin/env python3
"""
Sistema de Validação de Cumprimento de Punição (JJ's)

Este módulo implementa um sistema de validação para punições JJ's onde o militar
deve escrever por extenso todos os números de 1 até o número total da punição.

Funcionalidades:
- Monitoramento de canais privados de cumprimento
- Validação de mensagens por extenso em português
- Sistema de progresso e controle de erros
- Proteção contra spam e tentativas de burlar o sistema
- Integração com o sistema de punições existente
"""

import asyncio
import time
import re
import os
import json
from typing import Dict, Optional, Tuple, Any, List
from datetime import datetime
import logging

import disnake
from disnake.ext import commands
from disnake import Embed, Color

from config import BotConfig
from data_manager import data_manager


class JJValidationSystem(commands.Cog):
    """
    Sistema de Validação de Cumprimento de Punição JJ's
    
    Gerencia a validação de cumprimento de punições JJ's onde o militar
    deve escrever os números por extenso em ordem correta.
    """
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        
        # Configurações do sistema
        self.logger = logging.getLogger(__name__)
        
        # Dicionário para armazenar o progresso das punições em andamento
        # Estrutura: {user_id: {punishment_id, progresso_atual, quantidade_total, canal_id, erros}}
        self.active_jj_sessions: Dict[int, Dict] = {}
        
        # Controle de spam (anti-flood)
        self.user_message_times: Dict[int, List[float]] = {}
        self.max_messages_per_minute = 10  # Limite de mensagens por minuto
        self.time_window = 60  # Janela de tempo em segundos
        
        # Carrega sessões ativas do armazenamento persistente
        self.load_active_sessions()
        
        self.logger.info("Sistema de validação JJ's inicializado")
    
    def load_active_sessions(self):
        """
        Carrega sessões ativas de cumprimento de JJ's do armazenamento persistente.
        """
        try:
            # Carrega dados do arquivo de sessões ativas
            sessions_file = "data/jj_sessions.json"
            if os.path.exists(sessions_file):
                with open(sessions_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Converte chaves de string para int
                    self.active_jj_sessions = {int(user_id): session_data 
                                             for user_id, session_data in data.items()}
                self.logger.info(f"Sessões ativas carregadas: {len(self.active_jj_sessions)}")
            else:
                self.active_jj_sessions = {}
            
            # Não sincroniza canais existentes automaticamente
            # Isso será feito apenas quando o usuário usar o comando /iniciar-punicao-especifica
            
        except Exception as e:
            self.logger.error(f"Erro ao carregar sessões ativas: {e}")
            self.active_jj_sessions = {}
    
    def sync_existing_punishment_channels(self):
        """
        Sincroniza canais de punição existentes com o banco de dados de punições.
        Detecta canais privados de punição que já estão em andamento.
        """
        try:
            # Obtém todas as punições em cumprimento do banco de dados
            punishments, _ = data_manager.load_punishments()
            active_punishments = {}
            
            for punishment_id, punishment_data in punishments.items():
                if punishment_data.get("status") == "em_cumprimento":
                    active_punishments[punishment_id] = punishment_data
            
            if not active_punishments:
                self.logger.info("Nenhuma punição em cumprimento encontrada no banco de dados")
                return
            
            # Obtém o bot e os servidores
            if not self.bot.guilds:
                self.logger.warning("Nenhum servidor encontrado para sincronização")
                return
            
            guild = self.bot.guilds[0]  # Assume um único servidor ou pega o primeiro
            
            # Procura canais de punição existentes
            punishment_channels = []
            for channel in guild.text_channels:
                if self.is_jj_channel(channel):
                    punishment_channels.append(channel)
            
            if not punishment_channels:
                self.logger.info("Nenhum canal de punição encontrado nos servidores")
                return
            
            self.logger.info(f"Canais de punição encontrados: {len(punishment_channels)}")
            
            # Para cada canal de punição, tenta encontrar a punição correspondente
            for channel in punishment_channels:
                # Extrai o ID do usuário do nome do canal (formato: punicao-nome-do-usuario)
                # Exemplo: "punicao-joao-silva" -> tenta encontrar o usuário
                channel_name = channel.name
                punishment_name = channel_name.replace("punicao-", "")
                
                # Procura membros cujo nome corresponda ao canal
                matching_members = []
                for member in guild.members:
                    member_name_clean = member.name.lower().replace(" ", "-")
                    if member_name_clean == punishment_name:
                        matching_members.append(member)
                
                if not matching_members:
                    self.logger.warning(f"Nenhum membro encontrado para o canal {channel_name}")
                    continue
                
                # Usa o primeiro membro encontrado (caso haja nomes similares)
                user = matching_members[0]
                
                # Procura a punição correspondente para este usuário
                user_punishment = None
                for punishment_id, punishment_data in active_punishments.items():
                    if punishment_data.get("punido") == user.id:
                        user_punishment = punishment_data
                        break
                
                if not user_punishment:
                    self.logger.warning(f"Nenhuma punição em cumprimento encontrada para o usuário {user.name} no canal {channel_name}")
                    continue
                
                # Verifica se já existe sessão ativa para este usuário
                if user.id in self.active_jj_sessions:
                    self.logger.info(f"Sessão já ativa para o usuário {user.name}")
                    continue
                
                # Cria sessão ativa para a punição existente
                session = {
                    "punishment_id": user_punishment["id"] if "id" in user_punishment else list(active_punishments.keys())[0],
                    "progresso_atual": 0,  # Inicia do zero, pois não temos histórico
                    "quantidade_total": user_punishment["quantidade"],
                    "erros": 0,
                    "iniciado_em": time.time()
                }
                
                self.active_jj_sessions[user.id] = session
                self.logger.info(f"Sessão criada para punição existente: Usuário {user.name}, Canal {channel_name}, Quantidade {user_punishment['quantidade']}")
                
                # Envia mensagem de aviso no canal
                try:
                    embed = Embed(
                        title="🔄 Sistema JJ's Ativado",
                        description=f"O sistema de validação JJ's foi ativado para esta punição.",
                        color=Color.orange(),
                        timestamp=datetime.now()
                    )
                    
                    embed.add_field(
                        name="Usuário",
                        value=user.mention,
                        inline=True
                    )
                    
                    embed.add_field(
                        name="Quantidade",
                        value=f"**{user_punishment['quantidade']} JJ's**",
                        inline=True
                    )
                    
                    embed.add_field(
                        name="Status",
                        value="**Em Cumprimento**",
                        inline=True
                    )
                    
                    embed.add_field(
                        name="Instruções",
                        value=(
                            "1. Escreva os números de 1 a N por extenso em MAIÚSCULO\n"
                            "2. Cada número deve terminar com ponto de exclamação (!)\n"
                            "3. Não use números em formato numérico\n"
                            "4. Siga a ordem correta sem pular números\n"
                            "5. Quando terminar, digite `terminado`"
                        ),
                        inline=False
                    )
                    
                    embed.set_footer(text="O progresso será contado a partir de agora")
                    
                    asyncio.create_task(channel.send(embed=embed))
                    
                except Exception as e:
                    self.logger.error(f"Erro ao enviar mensagem de aviso no canal {channel_name}: {e}")
            
            # Salva as sessões criadas
            if self.active_jj_sessions:
                self.save_active_sessions()
                self.logger.info(f"Sincronização concluída. {len(self.active_jj_sessions)} sessões criadas para canais existentes")
            
        except Exception as e:
            self.logger.error(f"Erro ao sincronizar canais de punição existentes: {e}")
    
    def save_active_sessions(self):
        """
        Salva sessões ativas no armazenamento persistente.
        """
        try:
            sessions_file = "data/jj_sessions.json"
            # Cria diretório se não existir
            os.makedirs(os.path.dirname(sessions_file), exist_ok=True)
            
            # Converte chaves de int para string para o JSON
            sessions_data = {str(user_id): session_data 
                           for user_id, session_data in self.active_jj_sessions.items()}
            
            with open(sessions_file, 'w', encoding='utf-8') as f:
                json.dump(sessions_data, f, ensure_ascii=False, indent=2)
                
            self.logger.info(f"Sessões ativas salvas: {len(self.active_jj_sessions)}")
        except Exception as e:
            self.logger.error(f"Erro ao salvar sessões ativas: {e}")
    
    def number_to_words(self, number: int) -> str:
        """
        Converte um número para sua forma por extenso em português.
        
        Args:
            number: Número a ser convertido (1-9999)
            
        Returns:
            str: Número por extenso em MAIÚSCULO com ponto de exclamação
        """
        if number < 1 or number > 9999:
            raise ValueError("Número fora do intervalo permitido (1-9999)")
        
        unidades = ["", "UM", "DOIS", "TRÊS", "QUATRO", "CINCO", "SEIS", "SETE", "OITO", "NOVE"]
        dezenas = ["", "DEZ", "VINTE", "TRINTA", "QUARENTA", "CINQUENTA", "SESSENTA", "SETENTA", "OITENTA", "NOVENTA"]
        centenas = ["", "CENTO", "DUZENTOS", "TREZENTOS", "QUATROCENTOS", "QUINHENTOS", "SEISCENTOS", "SETECENTOS", "OITOCENTOS", "NOVECENTOS"]
        
        especiais = {
            11: "ONZE", 12: "DOZE", 13: "TREZE", 14: "QUATORZE", 15: "QUINZE",
            16: "DEZESSEIS", 17: "DEZESSETE", 18: "DEZOITO", 19: "DEZENOVE"
        }
        
        if number == 100:
            return "CEM!"
        
        milhares = number // 1000
        resto = number % 1000
        
        centenas_part = resto // 100
        dezenas_part = (resto % 100) // 10
        unidades_part = resto % 10
        
        result_parts = []
        
        # Parte dos milhares
        if milhares > 0:
            if milhares == 1:
                result_parts.append("MIL")
            else:
                result_parts.append(f"{unidades[milhares]} MIL")
        
        # Parte das centenas
        if centenas_part > 0:
            result_parts.append(centenas[centenas_part])
        
        # Parte das dezenas e unidades
        if resto > 0:
            if resto in especiais:
                result_parts.append(especiais[resto])
            else:
                if dezenas_part > 0:
                    result_parts.append(dezenas[dezenas_part])
                    if unidades_part > 0:
                        result_parts.append("E")
                if unidades_part > 0:
                    result_parts.append(unidades[unidades_part])
        
        # Junta todas as partes e adiciona o ponto de exclamação
        result = " ".join(result_parts).strip()
        return f"{result}!"
    
    def validate_message(self, message: str, expected_number: int) -> Tuple[bool, str]:
        """
        Valida se a mensagem corresponde ao número esperado.
        
        Args:
            message: Mensagem enviada pelo usuário
            expected_number: Número esperado
            
        Returns:
            Tuple[bool, str]: (é_válido, mensagem_de_erro_ou_sucesso)
        """
        # Remove espaços extras e converte para maiúsculo
        message_clean = message.strip().upper()
        
        # Verifica se contém números em formato numérico (não permitido)
        if re.search(r'\d', message_clean):
            return False, "❌ **Erro:** Não é permitido usar números em formato numérico. Use apenas a forma por extenso."
        
        # Verifica se termina com ponto de exclamação
        if not message_clean.endswith('!'):
            return False, "❌ **Erro:** A mensagem deve terminar com ponto de exclamação (!)."
        
        # Remove o ponto de exclamação para validação
        message_without_exclamation = message_clean.rstrip('!')
        
        # Obtém a forma correta por extenso
        try:
            correct_form = self.number_to_words(expected_number)
            correct_form_without_exclamation = correct_form.rstrip('!')
        except ValueError as e:
            return False, f"❌ **Erro interno:** {e}"
        
        # Compara exatamente com a forma correta
        if message_without_exclamation == correct_form_without_exclamation:
            return True, "✅ **Correto!**"
        else:
            # Verifica variações aceitáveis para números especiais
            if expected_number == 14 and message_without_exclamation == "CATORZE":
                return True, "✅ **Correto!**"
            return False, f"❌ **Erro:** Forma incorreta. O correto é: `{correct_form}`"
    
    def check_spam(self, user_id: int) -> bool:
        """
        Verifica se o usuário está enviando mensagens em excesso (spam).
        
        Args:
            user_id: ID do usuário
            
        Returns:
            bool: True se está enviando spam, False caso contrário
        """
        current_time = time.time()
        
        # Inicializa lista de tempos se não existir
        if user_id not in self.user_message_times:
            self.user_message_times[user_id] = []
        
        # Remove mensagens antigas (fora da janela de tempo)
        self.user_message_times[user_id] = [
            msg_time for msg_time in self.user_message_times[user_id] 
            if current_time - msg_time < self.time_window
        ]
        
        # Adiciona a mensagem atual
        self.user_message_times[user_id].append(current_time)
        
        # Verifica se excedeu o limite
        if len(self.user_message_times[user_id]) > self.max_messages_per_minute:
            return True
        
        return False
    
    def create_progress_embed(self, user: disnake.User, punishment_id: int, 
                            progress: int, total: int, errors: int) -> Embed:
        """
        Cria um embed mostrando o progresso do cumprimento da punição.
        
        Args:
            user: Usuário que está cumprindo
            punishment_id: ID da punição
            progress: Progresso atual
            total: Quantidade total
            errors: Número de erros
            
        Returns:
            Embed: Embed formatado com o progresso
        """
        embed = Embed(
            title="Progresso do Cumprimento de Punição JJ's",
            description=f"**Punição ID:** {punishment_id}",
            color=Color.blue(),
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name="Usuário",
            value=user.mention,
            inline=True
        )
        
        embed.add_field(
            name="Progresso",
            value=f"**{progress}/{total}** ({progress * 100 // total if total > 0 else 0}%)",
            inline=True
        )
        
        embed.add_field(
            name="Erros",
            value=f"**{errors}**",
            inline=True
        )
        
        # Barra de progresso visual
        progress_bar = self.create_progress_bar(progress, total)
        embed.add_field(
            name="Barra de Progresso",
            value=progress_bar,
            inline=False
        )
        
        embed.add_field(
            name="Próximo Número",
            value=f"**{progress + 1}**" if progress < total else "**Concluído!**",
            inline=True
        )
        
        embed.add_field(
            name="Status",
            value="**Em Cumprimento**" if progress < total else "**Concluído**",
            inline=True
        )
        
        embed.set_footer(text=f"Digite 'terminado' quando concluir todos os números")
        
        return embed
    
    def create_simple_progress_embed(self, user: disnake.User, punishment_id: int, 
                                   progress: int, total: int, errors: int) -> Embed:
        """
        Cria um embed simples mostrando o progresso sem a barra visual.
        Usado nas mensagens de validação de números.
        
        Args:
            user: Usuário que está cumprindo
            punishment_id: ID da punição
            progress: Progresso atual
            total: Quantidade total
            errors: Número de erros
            
        Returns:
            Embed: Embed formatado com o progresso (sem barra)
        """
        embed = Embed(
            title="Progresso do Cumprimento de Punição JJ's",
            description=f"**Punição ID:** {punishment_id}",
            color=Color.blue(),
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name="Usuário",
            value=user.mention,
            inline=True
        )
        
        embed.add_field(
            name="Progresso",
            value=f"**{progress}/{total}** ({progress * 100 // total if total > 0 else 0}%)",
            inline=True
        )
        
        embed.add_field(
            name="Erros",
            value=f"**{errors}**",
            inline=True
        )
        
        embed.add_field(
            name="Próximo Número",
            value=f"**{progress + 1}**" if progress < total else "**Concluído!**",
            inline=True
        )
        
        embed.add_field(
            name="Status",
            value="**Em Cumprimento**" if progress < total else "**Concluído**",
            inline=True
        )
        
        embed.set_footer(text=f"Digite 'terminado' quando concluir todos os números")
        
        return embed
    
    def create_progress_bar(self, current: int, total: int, length: int = 20) -> str:
        """
        Cria uma barra de progresso visual.
        
        Args:
            current: Valor atual
            total: Valor total
            length: Comprimento da barra
            
        Returns:
            str: Barra de progresso formatada
        """
        if total == 0:
            return "█" * length
        
        percentage = current / total
        filled = int(length * percentage)
        bar = "█" * filled + "░" * (length - filled)
        
        return f"`[{bar}]`"
    
    @commands.Cog.listener()
    async def on_message(self, message: disnake.Message):
        """
        Listener para mensagens que valida o cumprimento de punições JJ's.
        
        Args:
            message: Mensagem recebida
        """
        # Ignora mensagens de bots
        if message.author.bot:
            return
        
        # Verifica se é uma mensagem em um canal privado de cumprimento
        if not self.is_jj_channel(message.channel):
            return
        
        # Verifica se o usuário tem uma sessão ativa
        user_id = message.author.id
        if user_id not in self.active_jj_sessions:
            return
        
        session = self.active_jj_sessions[user_id]
        
        # Verifica se a punição ainda existe e está em cumprimento
        punishment_data = self.get_punishment_data(session["punishment_id"])
        if not punishment_data or punishment_data.get("status") != "em_cumprimento":
            # Remove sessão inválida
            del self.active_jj_sessions[user_id]
            self.save_active_sessions()
            return
        
        # Verifica se a mensagem está sendo enviada no canal correto para este usuário
        # Comentado para permitir mensagens em canais privados
        # if not self.is_valid_punishment_channel(message.channel, user_id):
        #     # Obtém o nome do canal correto para este usuário
        #     correct_channel_name = self.get_correct_channel_name(user_id)
        #     if correct_channel_name:
        #         await message.channel.send(
        #             f"⚠️ **Atenção {message.author.mention}!**\n"
        #             f"Esta mensagem só é válida no canal de punição criado especificamente para você.\n"
        #             f"Por favor, use o canal correto para cumprir sua punição: **#{correct_channel_name}**"
        #         )
        #     else:
        #         await message.channel.send(
        #             f"⚠️ **Atenção {message.author.mention}!**\n"
        #             f"Esta mensagem só é válida no canal de punição criado especificamente para você.\n"
        #             f"Por favor, use o canal correto para cumprir sua punição."
        #         )
        #     return
        
        
        # Processa a mensagem
        await self.process_jj_message(message, session)
    
    async def process_jj_message(self, message: disnake.Message, session: Dict):
        """
        Processa uma mensagem de cumprimento de punição JJ's.
        
        Args:
            message: Mensagem a ser processada
            session: Dados da sessão ativa
        """
        user = message.author
        punishment_id = session["punishment_id"]
        progress = session["progresso_atual"]
        total = session["quantidade_total"]
        
        # Verifica se a mensagem é "terminado"
        if message.content.strip().lower() == "terminado":
            await self.handle_termination(message, session)
            return
        
        # Valida a mensagem
        expected_number = progress + 1
        is_valid, validation_message = self.validate_message(message.content, expected_number)
        
        if is_valid:
            # Mensagem correta
            session["progresso_atual"] += 1
            progress = session["progresso_atual"]
            
            # Salva sessão atualizada IMEDIATAMENTE após cada progresso
            self.save_active_sessions()
            
            # Salva progresso no banco de dados de punições
            await self.save_progress_to_database(punishment_id, progress, session["erros"])
            
            # Não envia reação de confirmação
            # O feedback será mostrado apenas quando o comando /progresso for executado
            
            # Não envia embed de progresso a cada número
            # O progresso será mostrado apenas quando o comando /progresso for executado
            
            # Verifica se concluiu
            if progress >= total:
                await self.complete_punishment(message, session)
        else:
            # Mensagem incorreta
            session["erros"] += 1
            # Salva sessão atualizada IMEDIATAMENTE após cada erro
            self.save_active_sessions()
            
            # Salva erros no banco de dados de punições
            await self.save_progress_to_database(punishment_id, session["progresso_atual"], session["erros"])
            
            # Envia erro
            await message.add_reaction("❌")
            await message.channel.send(validation_message)
            
    
    async def handle_termination(self, message: disnake.Message, session: Dict):
        """
        Processa a tentativa de término da punição.
        
        Args:
            message: Mensagem contendo "terminado"
            session: Dados da sessão ativa
        """
        user = message.author
        progress = session["progresso_atual"]
        total = session["quantidade_total"]
        
        if progress >= total:
            # Conclusão válida
            await self.complete_punishment(message, session)
        else:
            # Tentativa de término inválida
            remaining = total - progress
            await message.channel.send(
                f"❌ **Conclusão Inválida!**\n"
                f"Faltam **{remaining}** números para concluir.\n"
                f"Por favor, continue escrevendo os números por extenso."
            )
    
    async def complete_punishment(self, message: disnake.Message, session: Dict):
        """
        Completa o cumprimento da punição.
        
        Args:
            message: Mensagem de conclusão
            session: Dados da sessão ativa
        """
        user = message.author
        punishment_id = session["punishment_id"]
        
        # Atualiza status da punição no banco de dados
        punishment_data = self.get_punishment_data(punishment_id)
        if punishment_data:
            punishment_data["status"] = "cumprida"
            punishment_data["data_conclusao"] = time.time()
            
            # Salva no banco de dados
            self.save_punishment_data(punishment_id, punishment_data)
            
            # Remove sessão ativa
            if user.id in self.active_jj_sessions:
                del self.active_jj_sessions[user.id]
                self.save_active_sessions()
            
            # Cria embed de conclusão
            embed = Embed(
                title="🎉 Punição Concluída com Sucesso!",
                description=f"**Punição ID:** {punishment_id}",
                color=Color.green(),
                timestamp=datetime.now()
            )
            
            embed.add_field(
                name="Usuário",
                value=user.mention,
                inline=True
            )
            
            embed.add_field(
                name="Quantidade",
                value=f"**{session['quantidade_total']} JJ's**",
                inline=True
            )
            
            embed.add_field(
                name="Erros",
                value=f"**{session['erros']}**",
                inline=True
            )
            
            embed.add_field(
                name="Data de Conclusão",
                value=f"<t:{int(time.time())}:F>",
                inline=True
            )
            
            embed.add_field(
                name="Status Final",
                value="**Concluída**",
                inline=True
            )
            
            embed.set_footer(text="Parabéns, punição finalizada!")
            
            # Envia no canal privado
            await message.channel.send(embed=embed)
            
            self.logger.info(f"Punição JJ's concluída: ID {punishment_id}, Usuário {user.id}, Erros: {session['erros']}")
        else:
            await message.channel.send("❌ **Erro:** Punição não encontrada no banco de dados.")
    
    async def block_punishment(self, message: disnake.Message, session: Dict):
        """
        Bloqueia o cumprimento da punição por excesso de erros.
        
        Args:
            message: Mensagem do usuário
            session: Dados da sessão ativa
        """
        user = message.author
        punishment_id = session["punishment_id"]
        
        embed = Embed(
            title="🚫 Punição Bloqueada!",
            description=f"**Punição ID:** {punishment_id}",
            color=Color.red(),
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name="Usuário",
            value=user.mention,
            inline=True
        )
        
        embed.add_field(
            name="Motivo",
            value="Excesso de erros (5+)",
            inline=True
        )
        
        embed.add_field(
            name="Erros",
            value=f"**{session['erros']}**",
            inline=True
        )
        
        embed.add_field(
            name="Progresso",
            value=f"**{session['progresso_atual']}/{session['quantidade_total']}**",
            inline=True
        )
        
        embed.set_footer(text="Contate um superior para redefinir a punição")
        
        await message.channel.send(embed=embed)
        
        # Remove sessão ativa
        if user.id in self.active_jj_sessions:
            del self.active_jj_sessions[user.id]
            self.save_active_sessions()
        
        self.logger.warning(f"Punição JJ's bloqueada: ID {punishment_id}, Usuário {user.id}, Erros: {session['erros']}")
    
    def is_jj_channel(self, channel: disnake.TextChannel) -> bool:
        """
        Verifica se o canal é um canal de cumprimento de JJ's.
        
        Args:
            channel: Canal a ser verificado
            
        Returns:
            bool: True se for um canal de JJ's, False caso contrário
        """
        # Verifica se o nome do canal começa com "punicao-"
        return channel.name.startswith("punicao-")
    
    def is_valid_punishment_channel(self, channel: disnake.TextChannel, user_id: int) -> bool:
        """
        Verifica se o canal é o canal correto para a punição do usuário.
        Garante que o militar só possa cumprir no canal específico criado para ele.
        
        Args:
            channel: Canal a ser verificado
            user_id: ID do usuário
            
        Returns:
            bool: True se for o canal correto, False caso contrário
        """
        # Primeiro verifica se é um canal de punição
        if not self.is_jj_channel(channel):
            return False
        
        # Obtém o bot e os servidores
        if not self.bot.guilds:
            return False
        
        guild = self.bot.guilds[0]  # Assume um único servidor ou pega o primeiro
        
        # Obtém o membro que está enviando a mensagem
        user = guild.get_member(user_id)
        if not user:
            return False
        
        # Gera o nome do canal esperado (formato: punicao-nome-do-usuario)
        expected_channel_name = f"punicao-{user.display_name.lower().replace(' ', '-')}"
        
        # Verifica se o nome do canal corresponde ao nome esperado
        return channel.name == expected_channel_name

    def get_correct_channel_name(self, user_id: int) -> Optional[str]:
        """
        Obtém o nome do canal correto para a punição do usuário.
        Busca o canal que corresponde ao usuário no servidor.
        
        Args:
            user_id: ID do usuário
            
        Returns:
            Optional[str]: Nome do canal correto ou None se não encontrado
        """
        # Obtém o bot e os servidores
        if not self.bot.guilds:
            return None
        
        guild = self.bot.guilds[0]  # Assume um único servidor ou pega o primeiro
        
        # Procura o membro correspondente ao user_id
        user = guild.get_member(user_id)
        if not user:
            return None
        
        # Gera o nome do canal esperado (formato: punicao-nome-do-usuario)
        expected_channel_name = f"punicao-{user.display_name.lower().replace(' ', '-')}"
        
        # Procura o canal no servidor
        for channel in guild.text_channels:
            if channel.name == expected_channel_name:
                return channel.name
        
        return None
    
    def get_punishment_data(self, punishment_id: int) -> Optional[Dict]:
        """
        Obtém os dados da punição do banco de dados.
        
        Args:
            punishment_id: ID da punição
            
        Returns:
            Optional[Dict]: Dados da punição ou None se não encontrada
        """
        try:
            # Força o ID para ser um inteiro
            pid = int(punishment_id)
            punishments, _ = data_manager.load_punishments()
            # data_manager.load_punishments() retorna as chaves como int
            return punishments.get(pid)
        except Exception as e:
            self.logger.error(f"Erro ao obter dados da punição {punishment_id}: {e}")
            return None
    
    def save_punishment_data(self, punishment_id: int, punishment_data: Dict):
        """
        Salva os dados atualizados da punição no banco de dados.
        
        Args:
            punishment_id: ID da punição
            punishment_data: Dados atualizados da punição
        """
        try:
            # Força o ID para ser um inteiro
            pid = int(punishment_id)
            punishments, counter = data_manager.load_punishments()
            punishments[pid] = punishment_data
            data_manager.save_punishments(punishments, counter)
        except Exception as e:
            self.logger.error(f"Erro ao salvar dados da punição {punishment_id}: {e}")
    
    async def save_progress_to_database(self, punishment_id: int, progress: int, errors: int):
        """
        Salva o progresso e erros da punição JJ's no banco de dados.
        Sincroniza os dados entre o arquivo de sessões e o banco de dados de punições.
        
        Args:
            punishment_id: ID da punição
            progress: Progresso atual
            errors: Número de erros
        """
        try:
            # Obtém os dados da punição
            punishment_data = self.get_punishment_data(punishment_id)
            if not punishment_data:
                self.logger.error(f"Punição {punishment_id} não encontrada para salvar progresso")
                return
            
            # Atualiza os campos de progresso e erros
            punishment_data["progresso_atual"] = progress
            punishment_data["erros"] = errors
            punishment_data["ultima_atualizacao"] = time.time()
            
            # Salva no banco de dados
            self.save_punishment_data(punishment_id, punishment_data)
            
            # Sincroniza com o arquivo de sessões ativas
            self.sync_session_with_database(punishment_id, progress, errors)
            
            self.logger.info(f"Progresso sincronizado: Punição {punishment_id}, Progresso {progress}/{punishment_data['quantidade']}, Erros: {errors}")
            
        except Exception as e:
            self.logger.error(f"Erro ao salvar progresso no banco de dados {punishment_id}: {e}")
    
    def sync_session_with_database(self, punishment_id: int, progress: int, errors: int):
        """
        Sincroniza a sessão ativa com o banco de dados de punições.
        Garante consistência entre os dois sistemas de armazenamento.
        
        Args:
            punishment_id: ID da punição
            progress: Progresso atual
            errors: Número de erros
        """
        try:
            # Procura a sessão ativa correspondente ao punishment_id
            for user_id, session in self.active_jj_sessions.items():
                if session.get("punishment_id") == punishment_id:
                    # Atualiza a sessão com os dados do banco de dados
                    session["progresso_atual"] = progress
                    session["erros"] = errors
                    session["ultima_atualizacao"] = time.time()
                    
                    # Salva a sessão atualizada
                    self.save_active_sessions()
                    
                    self.logger.info(f"Sessão sincronizada: Usuário {user_id}, Punição {punishment_id}, Progresso {progress}, Erros: {errors}")
                    break
            
        except Exception as e:
            self.logger.error(f"Erro ao sincronizar sessão com banco de dados {punishment_id}: {e}")
    
    async def iniciar_jj(
        self,
        user_id: int,
        punishment_id: int,
        quantidade: int,
        interaction: Optional[disnake.Interaction] = None
    ):
        """
        Inicia uma sessão de cumprimento JJ's.
        Este método pode ser chamado internamente ou por um comando.
        
        Args:
            user_id: ID do usuário que iniciará o cumprimento
            punishment_id: ID da punição
            quantidade: Quantidade total de JJ's
            interaction: Interação (opcional)
        """
        # Verifica se o usuário já tem uma sessão ativa
        if user_id in self.active_jj_sessions:
            if interaction:
                if not interaction.response.is_done():
                    await interaction.response.send_message("❌ **Erro:** Usuário já tem uma sessão de JJ's em andamento.", ephemeral=True)
                else:
                    await interaction.followup.send("❌ **Erro:** Usuário já tem uma sessão de JJ's em andamento.", ephemeral=True)
            return
        
        # Cria nova sessão
        session = {
            "punishment_id": punishment_id,
            "progresso_atual": 0,
            "quantidade_total": quantidade,
            "erros": 0,
            "iniciado_em": time.time()
        }
        
        self.active_jj_sessions[user_id] = session
        self.save_active_sessions()
        
        # Obtém o usuário
        user = self.bot.get_user(user_id)
        
        # Cria embed de início
        embed = Embed(
            title="🎯 Início do Cumprimento de Punição JJ's",
            description=f"**Punição ID:** {punishment_id}",
            color=Color.green(),
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name="Usuário",
            value=user.mention if user else f"<@{user_id}>",
            inline=True
        )
        
        embed.add_field(
            name="Quantidade",
            value=f"**{quantidade} JJ's**",
            inline=True
        )
        
        embed.add_field(
            name="Status",
            value="**Em Cumprimento**",
            inline=True
        )
        
        embed.add_field(
            name="Instruções",
            value=(
                "1. Escreva os números de 1 a N por extenso em MAIÚSCULO\n"
                "2. Cada número deve terminar com ponto de exclamação (!)\n"
                "3. Não use números em formato numérico\n"
                "4. Siga a ordem correta sem pular números\n"
                "5. Quando terminar, digite `terminado`"
            ),
            inline=False
        )
        
        embed.set_footer(text="Boa sorte no cumprimento!")
        
        if interaction:
            if not interaction.response.is_done():
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                await interaction.followup.send(embed=embed, ephemeral=True)
        
        self.logger.info(f"Sessão JJ's iniciada: Usuário {user_id}, Punição {punishment_id}, Quantidade {quantidade}")
    
    @commands.slash_command(
        name="progresso",
        description="Mostra o progresso atual do cumprimento de punição JJ's."
    )
    async def progresso(
        self,
        interaction: disnake.ApplicationCommandInteraction
    ):
        """
        Comando para mostrar o progresso atual do cumprimento de punição JJ's.
        Mostra a barra de progresso visual completa.
        Agora permite visualizar múltiplas punições simultâneas.
        
        Args:
            interaction: Interação do comando
        """
        user_id = interaction.author.id
        
        # Obtém todas as punições do usuário (pendentes ou pausadas)
        punishments, _ = data_manager.load_punishments()
        user_punishments = {}
        
        for punishment_id, punishment_data in punishments.items():
            if punishment_data.get("punido") == user_id and punishment_data.get("status") in ["pendente", "pausada", "em_cumprimento"]:
                user_punishments[punishment_id] = punishment_data
        
        if not user_punishments:
            await interaction.response.send_message(
                "❌ **Erro:** Você não tem punições para cumprir.",
                ephemeral=True
            )
            return
        
        # Cria embed com barra de progresso para cada punição do usuário
        embed = Embed(
            title="Progresso do Cumprimento de Punição JJ's",
            description=f"**Usuário:** {interaction.author.mention}",
            color=Color.blue(),
            timestamp=datetime.now()
        )
        
        # Ordena punições por ID para exibição consistente
        for punishment_id in sorted(user_punishments.keys()):
            punishment_data = user_punishments[punishment_id]
            
            # Tenta encontrar uma sessão ativa para esta punição
            # Nota: Atualmente o sistema permite apenas uma sessão ativa por usuário
            session = self.active_jj_sessions.get(user_id)
            is_active = session and session.get("punishment_id") == punishment_id
            
            if is_active:
                progress = session.get("progresso_atual", 0)
                total = session.get("quantidade_total", 0)
                errors = session.get("erros", 0)
                status_text = "⚡ Em Cumprimento"
            else:
                progress = punishment_data.get("progresso_atual", 0)
                total = punishment_data.get("quantidade", 0)
                errors = punishment_data.get("erros", 0)
                status_text = "⏸️ Pausada" if punishment_data.get("status") == "pausada" else "⏳ Pendente"
            
            # Barra de progresso visual
            progress_bar = self.create_progress_bar(progress, total)
            
            percentage = (progress * 100 // total) if total > 0 else 0
            
            embed.add_field(
                name=f"**Punição ID {punishment_id}**",
                value=(
                    f"**Progresso:** {progress}/{total} ({percentage}%)\n"
                    f"**Erros:** {errors}\n"
                    f"**Próximo Número:** {progress + 1 if progress < total else 'Concluído!'}\n"
                    f"**Status:** {status_text}\n"
                    f"**Barra:** {progress_bar}"
                ),
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    
    @commands.slash_command(
        name="pausar-punicao",
        description="Pausa o cumprimento de uma punição JJ's."
    )
    async def pausar_punicao(
        self,
        interaction: disnake.ApplicationCommandInteraction
    ):
        """
        Comando para pausar o cumprimento de uma punição JJ's.
        O militar pode usar este comando quando quiser pausar.
        
        Args:
            interaction: Interação do comando
        """
        user_id = interaction.author.id
        
        # Verifica se o usuário tem uma sessão ativa
        if user_id not in self.active_jj_sessions:
            await interaction.response.send_message(
                "❌ **Erro:** Você não tem uma punição JJ's em andamento.",
                ephemeral=True
            )
            return
        
        session = self.active_jj_sessions[user_id]
        
        # Verifica se a punição ainda existe e está em cumprimento
        punishment_data = self.get_punishment_data(session["punishment_id"])
        if not punishment_data or punishment_data.get("status") != "em_cumprimento":
            # Remove sessão inválida
            del self.active_jj_sessions[user_id]
            self.save_active_sessions()
            await interaction.response.send_message(
                "❌ **Erro:** Punição não encontrada ou já concluída.",
                ephemeral=True
            )
            return
        
        # Salva a sessão no arquivo de sessões antes de remover (para preservar progresso)
        # Primeiro, carrega sessões existentes
        try:
            sessions_file = "data/jj_sessions.json"
            saved_sessions = {}
            if os.path.exists(sessions_file):
                with open(sessions_file, 'r', encoding='utf-8') as f:
                    saved_sessions = json.load(f)
            
            # Salva a sessão atual (com progresso e erros)
            saved_sessions[str(user_id)] = session
            
            # Salva no arquivo
            with open(sessions_file, 'w', encoding='utf-8') as f:
                json.dump(saved_sessions, f, ensure_ascii=False, indent=2)
                
            self.logger.info(f"Sessão salva antes de pausar: Usuário {user_id}, Progresso {session['progresso_atual']}/{session['quantidade_total']}")
            
        except Exception as e:
            self.logger.error(f"Erro ao salvar sessão antes de pausar: {e}")
        
        # Atualiza status da punição para "pausada"
        punishment_data["status"] = "pausada"
        punishment_data["data_pausa"] = time.time()
        self.save_punishment_data(session["punishment_id"], punishment_data)
        
        # Remove sessão ativa da memória
        del self.active_jj_sessions[user_id]
        self.save_active_sessions()
        
        # Cria embed de pausa
        embed = Embed(
            title="⏸️ Punição Pausada",
            description=f"**Punição ID:** {session['punishment_id']}",
            color=Color.orange(),
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name="Usuário",
            value=interaction.author.mention,
            inline=True
        )
        
        embed.add_field(
            name="Progresso Atual",
            value=f"**{session['progresso_atual']}/{session['quantidade_total']}**",
            inline=True
        )
        
        embed.add_field(
            name="Erros",
            value=f"**{session['erros']}**",
            inline=True
        )
        
        embed.add_field(
            name="Status",
            value="**Pausada**",
            inline=True
        )
        
        embed.add_field(
            name="Observação",
            value="Para retomar o cumprimento, use o comando `/iniciar-punicao-especifica` novamente.",
            inline=False
        )
        
        embed.set_footer(text="Punição pausada com sucesso")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
        self.logger.info(f"Punição JJ's pausada: Usuário {user_id}, Punição {session['punishment_id']}, Progresso {session['progresso_atual']}/{session['quantidade_total']}")
    
    @commands.slash_command(
        name="iniciar-punicao-especifica",
        description="Inicia o cumprimento de uma punição JJ's específica."
    )
    async def iniciar_punicao_especifica(
        self,
        interaction: disnake.ApplicationCommandInteraction,
        punishment_id: int = commands.Param(description="ID da punição que deseja iniciar")
    ):
        """
        Comando para iniciar o cumprimento de uma punição JJ's específica.
        Permite ao militar escolher qual punição iniciar entre as disponíveis.
        
        Args:
            interaction: Interação do comando
            punishment_id: ID da punição a ser iniciada
        """
        user_id = interaction.author.id
        
        # Obtém todas as punições do usuário (pendentes ou pausadas)
        punishments, _ = data_manager.load_punishments()
        user_punishments = {}
        
        for pid, punishment_data in punishments.items():
            if punishment_data.get("punido") == user_id and punishment_data.get("status") in ["pendente", "pausada"]:
                user_punishments[pid] = punishment_data
        
        if not user_punishments:
            await interaction.response.send_message(
                "❌ **Erro:** Você não tem punições pendentes ou pausadas para cumprir.",
                ephemeral=True
            )
            return
        
        # Verifica se a punição escolhida existe e está disponível
        if punishment_id not in user_punishments:
            await interaction.response.send_message(
                f"❌ **Erro:** Punição ID {punishment_id} não encontrada ou não está disponível para cumprimento.",
                ephemeral=True
            )
            return
        
        # Verifica se o usuário já tem sessões ativas
        user_sessions = {pid: session for pid, session in self.active_jj_sessions.items() 
                        if session.get("punishment_id") in user_punishments}
        
        if user_sessions:
            # Lista as punições já em andamento
            active_punishments = []
            for pid, session in user_sessions.items():
                punishment_data = user_punishments.get(pid)
                if punishment_data:
                    active_punishments.append(f"**ID {pid}:** {punishment_data['quantidade']} JJ's ({session['progresso_atual']}/{session['quantidade_total']})")
            
            await interaction.response.send_message(
                f"⚠️ **Aviso:** Você já tem {len(user_sessions)} punição(ões) em andamento:\n" + 
                "\n".join(active_punishments) + 
                f"\n\n**Dica:** Use o comando `/progresso` para ver o status das punições ativas.",
                ephemeral=True
            )
            return
        
        punishment_data = user_punishments[punishment_id]
        
        # Verifica se há progresso salvo para esta punição (caso tenha sido pausada anteriormente)
        saved_progress = 0
        saved_errors = 0
        
        # Primeiro procura no banco de dados de punições
        try:
            punishment_data_db = self.get_punishment_data(punishment_id)
            if punishment_data_db:
                saved_progress = punishment_data_db.get("progresso_atual", 0)
                saved_errors = punishment_data_db.get("erros", 0)
                self.logger.info(f"Progresso carregado do banco de dados: {saved_progress}/{punishment_data['quantidade']}, Erros: {saved_errors}")
        except Exception as e:
            self.logger.warning(f"Erro ao carregar progresso do banco de dados: {e}")
        
        # Se não encontrar no banco de dados, procura nas sessões salvas (arquivo de sessões ativas)
        if saved_progress == 0 and saved_errors == 0:
            try:
                sessions_file = "data/jj_sessions.json"
                if os.path.exists(sessions_file):
                    with open(sessions_file, 'r', encoding='utf-8') as f:
                        saved_sessions = json.load(f)
                        # Procura sessão com o mesmo punishment_id
                        for saved_user_id, saved_session in saved_sessions.items():
                            if saved_session.get("punishment_id") == punishment_id:
                                saved_progress = saved_session.get("progresso_atual", 0)
                                saved_errors = saved_session.get("erros", 0)
                                self.logger.info(f"Progresso carregado de sessões salvas: {saved_progress}/{punishment_data['quantidade']}, Erros: {saved_errors}")
                                break
            except Exception as e:
                self.logger.warning(f"Erro ao carregar progresso salvo: {e}")
        
        # Cria nova sessão (ou retoma progresso)
        session = {
            "punishment_id": punishment_id,
            "progresso_atual": saved_progress,
            "quantidade_total": punishment_data["quantidade"],
            "erros": saved_errors,
            "iniciado_em": time.time()
        }
        
        self.active_jj_sessions[user_id] = session
        self.save_active_sessions()
        
        # Atualiza status da punição para "em_cumprimento"
        punishment_data["status"] = "em_cumprimento"
        punishment_data["data_inicio_cumprimento"] = time.time()
        self.save_punishment_data(punishment_id, punishment_data)
        
        # Cria embed de início
        embed = Embed(
            title="🎯 Início do Cumprimento de Punição JJ's",
            description=f"**Punição ID:** {punishment_id}",
            color=Color.green(),
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name="Usuário",
            value=interaction.author.mention,
            inline=True
        )
        
        embed.add_field(
            name="Quantidade",
            value=f"**{punishment_data['quantidade']} JJ's**",
            inline=True
        )
        
        embed.add_field(
            name="Progresso Inicial",
            value=f"**{saved_progress}/{punishment_data['quantidade']}**",
            inline=True
        )
        
        embed.add_field(
            name="Erros Iniciais",
            value=f"**{saved_errors}**",
            inline=True
        )
        
        embed.add_field(
            name="Status",
            value="**Em Cumprimento**",
            inline=True
        )
        
        embed.add_field(
            name="Instruções",
            value=(
                "1. Escreva os números de 1 a N por extenso em MAIÚSCULO\n"
                "2. Cada número deve terminar com ponto de exclamação (!)\n"
                "3. Não use números em formato numérico\n"
                "4. Siga a ordem correta sem pular números\n"
                "5. Quando terminar, digite `terminado`\n"
                "6. **Importante:** Só envie mensagens neste canal!"
            ),
            inline=False
        )
        
        embed.set_footer(text="Boa sorte no cumprimento!")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
        self.logger.info(f"Punição JJ's iniciada via comando específico: Usuário {user_id}, Punição {punishment_id}, Quantidade {punishment_data['quantidade']}, Progresso Inicial {saved_progress}")


def setup(bot: commands.Bot):
    """
    Função de setup para registrar o cog no bot.
    
    Args:
        bot: Instância do bot
    """
    bot.add_cog(JJValidationSystem(bot))
