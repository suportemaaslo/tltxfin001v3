import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from typing import Optional
import re
import socket

class GmailService:
    def __init__(self, services, dicCredentials, dicParameters):
        self.services = services
        self.dicCredentials = dicCredentials
        self.dicParameters = dicParameters

        self.credGmailDomain = self.dicCredentials["credGmailDomain"]
        self.credGmailPort = int(self.dicCredentials["credGmailPort"])  # geralmente 587
        self.credGmailEmail = self.dicCredentials["credGmailEmail"]
        self.credGmailAppPassword = self.dicCredentials["credGmailAppPassword"]

    def _sanitize_domain(self, domain: str) -> str:
        d = (domain or "").strip().lower()
        if d.startswith("http://"):
            d = d[len("http://"):]
        elif d.startswith("https://"):
            d = d[len("https://"):]
        # remove caracteres não desejados nas pontas
        d = d.strip("` ;")
        return d

    def _load_template(self, template_name: str) -> str:
        base_path = Path("src/template/email")
        template_path = base_path / template_name
        try:
            return template_path.read_text(encoding="utf-8")
        except Exception:
            return ""  # fallback para gerar corpo padrão se não existir

    def _resolve_recipients(self) -> list:
        # Resolve destinatários a partir dos parâmetros ou config.json
        recipients = (
            self.dicParameters.get("notificationEmail")
            or self.dicParameters.get("notificationEmailList")
            or self.dicParameters.get("emailDestinatario")
        )

        if isinstance(recipients, str):
            parsed = [email.strip() for email in recipients.split(",") if email.strip()]
            if parsed:
                return parsed
        elif isinstance(recipients, list) and recipients:
            return recipients

        # Fallback: usa o remetente configurado
        return [self.credGmailEmail]

    def _log_email_error(
        self,
        stage: str,
        error: Exception,
        subject: str,
        idexecucao: int,
        idtransacao: Optional[int],
        recipients: list,
    ) -> None:
        try:
            line = self.services.traceback.extract_tb(error.__traceback__)[-1][1]
        except Exception:
            line = None
        err_type = type(error).__name__
        hint = "Verifique 'credGmailDomain' (ex.: smtp.gmail.com) e DNS/resolução de nome; porta típica 587."
        msg = (
            f"[EmailError] stage={stage}; type={err_type}; msg={str(error)}; "
            f"smtp_domain={self.credGmailDomain}; smtp_port={self.credGmailPort}; "
            f"recipients={', '.join(recipients)}; subject={subject}; exec={idexecucao}; tx={idtransacao or ''}; "
            f"hint={hint}"
        )
        try:
            if line is not None:
                self.services.logger.log_error("enviaremail", f"{msg} - line: {line}")
            else:
                self.services.logger.log_error("enviaremail", msg)
        except Exception:
            pass

    def enviaremail(
        self,
        tipoemail: str,
        Subject: str,
        idexecucao: int,
        idtransacao: Optional[int] = None,
        mensagem: Optional[str] = None,
    ) -> bool:
        tipo = (tipoemail or "").strip().lower()
        if tipo not in {"start", "finish", "error"}:
            raise ValueError("tipoemail deve ser 'Start', 'Finish' ou 'Error'")

        if not Subject:
            raise ValueError("Subject é obrigatório")
        if idexecucao is None:
            raise ValueError("idexecucao é obrigatório")

        if tipo == "start":
            template_html = self._load_template("bodyStart.html")
            if not template_html:
                template_html = (
                    "<html><body><h3>Início de Processo</h3>"
                    "<p>O processo {{PROCESS_NAME}} foi iniciado.</p>"
                    "<p>ID da Execução: <strong>{{IDEXECUTION}}</strong></p>"
                    "<p>Você receberá um e-mail adicional quando o processo for concluído.</p>"
                    "</body></html>"
                )
        elif tipo == "finish":
            template_html = self._load_template("bodyFinish.html")
            if not template_html:
                template_html = (
                    "<html><body><h3>Conclusão de Processo</h3>"
                    "<p>O processo {{PROCESS_NAME}} foi concluído com sucesso.</p>"
                    "<p>ID da Execução: <strong>{{IDEXECUTION}}</strong></p>"
                    "</body></html>"
                )
        else:
            template_html = self._load_template("bodyError.html")
            if not template_html:
                template_html = (
                    "<html><body><h3>Alerta de Erro no Processo</h3>"
                    "<p>O processo {{PROCESS_NAME}} foi interrompido.</p>"
                    "<p>ID da Execução: <strong>{{IDEXECUTION}}</strong></p>"
                    "<p>ID da Transação: <strong>{{IDTRANSACTION}}</strong></p>"
                    "<p>Item específico: {{ERROR_ITEM}}</p>"
                    "<p>Mensagem de erro: {{ERROR_MESSAGE}}</p>"
                    "<p>Linha do erro: {{ERROR_LINE}}</p>"
                    "<p>Contexto: {{ERROR_CONTEXT}}</p>"
                    "</body></html>"
                )

        # Dados dinâmicos comuns
        process_name = self.dicParameters.get("processName", "N/A")
        transaction_label = f"Transação {idtransacao}" if idtransacao is not None else ""

        # Extração de detalhes de erro a partir de 'mensagem' quando aplicável
        error_item = transaction_label
        error_message = mensagem or ""
        error_line = ""
        error_context = self.dicParameters.get("robotName", self.dicParameters.get("processName", ""))
        if error_message:
            m_line = re.search(r"Line\s*[:=]\s*(\d+)", error_message, re.IGNORECASE)
            if m_line:
                error_line = m_line.group(1)

        body_html = (
            template_html
            .replace("{{PROCESS_NAME}}", process_name)
            .replace("{{IDEXECUTION}}", str(idexecucao))
            .replace("{{IDTRANSACTION}}", str(idtransacao) if idtransacao is not None else "")
            .replace("{{MESSAGE}}", error_message)
            .replace("{{ERROR_ITEM}}", error_item)
            .replace("{{ERROR_MESSAGE}}", error_message)
            .replace("{{ERROR_LINE}}", error_line)
            .replace("{{ERROR_CONTEXT}}", error_context)
        )

        recipients = self._resolve_recipients()

        msg = MIMEMultipart("alternative")
        msg["From"] = self.credGmailEmail
        msg["To"] = ", ".join(recipients)
        msg["Subject"] = Subject
        msg.attach(MIMEText(body_html, "html", "utf-8"))

        # Pré-validação de DNS
        try:
            smtp_domain = self._sanitize_domain(self.credGmailDomain)
            socket.getaddrinfo(smtp_domain, self.credGmailPort)
        except Exception as e:
            self._log_email_error("dns_lookup", e, Subject, idexecucao, idtransacao, recipients)
            return False

        # Conexão SMTP e envio
        try:
            smtp_domain = self._sanitize_domain(self.credGmailDomain)
            with smtplib.SMTP(smtp_domain, self.credGmailPort, timeout=30) as server:
                try:
                    server.starttls()
                except Exception as e_tls:
                    self._log_email_error("smtp_starttls", e_tls, Subject, idexecucao, idtransacao, recipients)
                    return False

                try:
                    server.login(self.credGmailEmail, self.credGmailAppPassword)
                except Exception as e_login:
                    self._log_email_error("smtp_login", e_login, Subject, idexecucao, idtransacao, recipients)
                    return False

                try:
                    server.sendmail(self.credGmailEmail, recipients, msg.as_string())
                except Exception as e_send:
                    self._log_email_error("smtp_send", e_send, Subject, idexecucao, idtransacao, recipients)
                    return False

            # Log de sucesso
            try:
                self.services.logger.log_info(
                    "enviaremail",
                    f"Email '{tipoemail}' enviado para: {', '.join(recipients)} | Execução: {idexecucao} | Transação: {idtransacao or ''}"
                )
            except Exception:
                pass
            return True
        except Exception as e:
            self._log_email_error("smtp_connect", e, Subject, idexecucao, idtransacao, recipients)
            return False

        